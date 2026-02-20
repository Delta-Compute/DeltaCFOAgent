/**
 * WhatsApp Web Bridge with Firestore Integration
 *
 * This bridge connects to Firestore and manages WhatsApp sessions:
 * 1. Watches for sessions with status 'connecting'
 * 2. Generates QR codes and stores them in Firestore
 * 3. Stores incoming messages in Firestore
 *
 * Run with: npx tsx whatsapp-bridge-firestore.ts
 */

import pkg from 'whatsapp-web.js';
const { Client, LocalAuth } = pkg;
type Message = pkg.Message;
type ClientType = InstanceType<typeof Client>;
import qrcode from 'qrcode-terminal';
import * as path from 'path';
import * as fs from 'fs';
import { initializeApp, cert, getApps } from 'firebase-admin/app';
import { getFirestore, Timestamp, FieldValue } from 'firebase-admin/firestore';

// Initialize Firebase Admin
function initFirebase() {
  if (getApps().length > 0) {
    return getFirestore();
  }

  let serviceAccount;

  // Option 1: Load from environment variable (for Railway/production)
  if (process.env.FIREBASE_CREDENTIALS) {
    try {
      serviceAccount = JSON.parse(process.env.FIREBASE_CREDENTIALS);
      console.log('[BRIDGE] Loaded credentials from FIREBASE_CREDENTIALS env var');
    } catch (e) {
      throw new Error('Invalid FIREBASE_CREDENTIALS environment variable - must be valid JSON');
    }
  } else {
    // Option 2: Load from firebase-credentials.json file (for local development)
    const credPath = path.join(process.cwd(), 'firebase-credentials.json');
    if (!fs.existsSync(credPath)) {
      throw new Error('Firebase credentials required. Set FIREBASE_CREDENTIALS env var or create firebase-credentials.json file.');
    }

    const credFile = fs.readFileSync(credPath, 'utf8');
    serviceAccount = JSON.parse(credFile);
    console.log('[BRIDGE] Loaded credentials from firebase-credentials.json');
  }

  initializeApp({
    credential: cert(serviceAccount),
  });

  return getFirestore();
}

const db = initFirebase();

// OTP patterns
const OTP_PATTERNS = [
  /codigo[:\s]*(\d{4,6})/i,
  /code[:\s]*(\d{4,6})/i,
  /verification[:\s]*(\d{4,6})/i,
  /verificacao[:\s]*(\d{4,6})/i,
  /otp[:\s]*(\d{4,6})/i,
  /(?:^|\s)(\d{4,6})(?:\s|$)/,
];

// Platform detection
const PLATFORM_PATTERNS = {
  ifood: [/ifood/i],
  rappi: [/rappi/i],
};

interface SessionData {
  id: string;
  userId: string;
  sessionIndex: number;
  status: string;
}

class WhatsAppBridgeFirestore {
  private clients: Map<string, ClientType> = new Map();
  private sessionBasePath: string;
  private isShuttingDown: boolean = false;
  private handledSessions: Set<string> = new Set(); // Track sessions we've handled this run

  constructor() {
    this.sessionBasePath = path.join(process.cwd(), '.whatsapp-sessions');
  }

  /**
   * Start watching for sessions that need QR codes
   */
  async start(): Promise<void> {
    console.log('[BRIDGE] Starting WhatsApp Bridge with Firestore...');

    // First, show all existing sessions for debugging
    console.log('[BRIDGE] Checking all existing sessions...');
    const allSessions = await db.collection('sessions').get();
    if (allSessions.empty) {
      console.log('[BRIDGE] No sessions found in Firestore');
    } else {
      console.log(`[BRIDGE] Found ${allSessions.size} session(s):`);
      allSessions.docs.forEach((doc) => {
        const data = doc.data();
        console.log(`[BRIDGE]   - ${doc.id}: status="${data.status}", userId="${data.userId}"`);
      });
    }

    console.log('[BRIDGE] Watching for sessions with status "connecting"...');

    // Watch for sessions that need to connect
    db.collection('sessions')
      .where('status', '==', 'connecting')
      .onSnapshot((snapshot) => {
        console.log(`[BRIDGE] Snapshot received: ${snapshot.size} connecting session(s)`);
        snapshot.docChanges().forEach((change) => {
          console.log(`[BRIDGE] Change detected: type=${change.type}, id=${change.doc.id}`);
          if (change.type === 'added' || change.type === 'modified') {
            const session = { id: change.doc.id, ...change.doc.data() } as SessionData;
            console.log(`[BRIDGE] Session ${session.id} needs connection`);
            this.handleSession(session);
          }
        });
      }, (error) => {
        console.error('[BRIDGE] Firestore listener error:', error);
      });

    // Also check for any sessions that need reconnection
    const pendingSessions = await db.collection('sessions')
      .where('status', '==', 'connecting')
      .get();

    console.log(`[BRIDGE] Initial check: ${pendingSessions.size} session(s) with status "connecting"`);

    for (const doc of pendingSessions.docs) {
      const session = { id: doc.id, ...doc.data() } as SessionData;
      this.handleSession(session);
    }

    // Auto-reconnect sessions that are already connected (maintains connection across bridge restarts)
    const connectedSessions = await db.collection('sessions')
      .where('status', '==', 'connected')
      .get();

    console.log(`[BRIDGE] Found ${connectedSessions.size} already-connected session(s) to reconnect`);

    for (const doc of connectedSessions.docs) {
      const session = { id: doc.id, ...doc.data() } as SessionData;
      console.log(`[BRIDGE] Auto-reconnecting session ${session.id}...`);
      this.handleSession(session);
    }

    console.log('[BRIDGE] Bridge is running. Press Ctrl+C to stop.');
    console.log('[BRIDGE] Now go to the dashboard and click "Generate QR Code"');
  }

  /**
   * Clean up Chrome lock files that prevent restart
   */
  private cleanupLockFiles(sessionPath: string): void {
    const lockFiles = ['SingletonLock', 'SingletonSocket', 'SingletonCookie'];
    for (const lockFile of lockFiles) {
      const lockPath = path.join(sessionPath, 'session-' + path.basename(sessionPath), lockFile);
      try {
        if (fs.existsSync(lockPath)) {
          fs.unlinkSync(lockPath);
          console.log(`[BRIDGE] Cleaned up lock file: ${lockFile}`);
        }
      } catch {
        // Ignore errors
      }
    }
  }

  /**
   * Handle a session that needs to connect
   */
  private async handleSession(session: SessionData): Promise<void> {
    // Skip if we already have a client for this session
    if (this.clients.has(session.id)) {
      console.log(`[BRIDGE] Already have active client for session ${session.id}`);
      return;
    }

    // Skip if we've already handled this session in this bridge run
    if (this.handledSessions.has(session.id)) {
      console.log(`[BRIDGE] Already handled session ${session.id} this run, skipping`);
      return;
    }

    // Mark as handled
    this.handledSessions.add(session.id);

    console.log(`[BRIDGE] Initializing WhatsApp client for session ${session.id}`);

    const sessionPath = path.join(this.sessionBasePath, session.id);

    // Clean up any stale lock files from previous runs
    this.cleanupLockFiles(sessionPath);

    // Use 'new' headless mode on server (more compatible), visible browser locally
    const isServer = !!process.env.PUPPETEER_EXECUTABLE_PATH;
    const puppeteerOptions: Record<string, unknown> = {
      headless: isServer ? 'new' : false, // 'new' headless mode is more browser-like
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--no-first-run',
        '--disable-gpu',
        '--disable-software-rasterizer',
        '--disable-web-security',
        '--allow-running-insecure-content',
      ],
    };

    // Use system Chrome if PUPPETEER_EXECUTABLE_PATH is set (Docker environment)
    if (process.env.PUPPETEER_EXECUTABLE_PATH) {
      puppeteerOptions.executablePath = process.env.PUPPETEER_EXECUTABLE_PATH;
      console.log(`[BRIDGE] Using Chrome at: ${process.env.PUPPETEER_EXECUTABLE_PATH}`);
    }

    const client = new Client({
      authStrategy: new LocalAuth({
        dataPath: sessionPath,
        clientId: session.id,
      }),
      puppeteer: puppeteerOptions,
      qrMaxRetries: 10,  // Allow more QR retries before giving up (each QR lasts ~20s)
    });

    this.clients.set(session.id, client);


    // Track QR attempts
    let qrAttempts = 0;

    // QR code event
    client.on('qr', async (qr: string) => {
      // Don't process QR during shutdown
      if (this.isShuttingDown) {
        console.log(`[BRIDGE] Ignoring QR event during shutdown`);
        return;
      }

      qrAttempts++;
      console.log(`[BRIDGE] ========================================`);
      console.log(`[BRIDGE] QR CODE #${qrAttempts} for session ${session.id}`);
      console.log(`[BRIDGE] QR data length: ${qr.length} chars`);
      console.log(`[BRIDGE] Scan this QR code with WhatsApp:`);
      qrcode.generate(qr, { small: true });
      console.log(`[BRIDGE] ========================================`);

      // Store QR code in Firestore
      // Note: If QR is being generated, the client is NOT connected - always update status
      try {
        await db.collection('sessions').doc(session.id).update({
          status: 'qr_pending',
          qrCode: qr,
          qrAttempts,
          lastActivity: Timestamp.now(),
        });
        console.log(`[BRIDGE] QR code saved to Firestore`);
      } catch (err) {
        console.error(`[BRIDGE] Failed to save QR to Firestore:`, err);
      }
    });

    // Loading screen event (happens during initialization)
    client.on('loading_screen', (percent: number, message: string) => {
      console.log(`[BRIDGE] Loading: ${percent}% - ${message}`);
    });

    // Authenticated event (QR scan successful, before ready)
    client.on('authenticated', () => {
      console.log(`[BRIDGE] ========================================`);
      console.log(`[BRIDGE] AUTHENTICATED! Session ${session.id}`);
      console.log(`[BRIDGE] QR scan was successful, waiting for ready...`);
      console.log(`[BRIDGE] ========================================`);
    });

    // State change event
    client.on('change_state', (state: string) => {
      console.log(`[BRIDGE] State changed for ${session.id}: ${state}`);
    });

    // Ready event
    client.on('ready', async () => {
      console.log(`[BRIDGE] ========================================`);
      console.log(`[BRIDGE] READY! Session ${session.id} is fully connected!`);
      console.log(`[BRIDGE] ========================================`);

      try {
        const info = client.info;
        const phone = info?.wid?.user || 'Unknown';
        console.log(`[BRIDGE] Phone number: ${phone}`);
        console.log(`[BRIDGE] Updating Firestore status to "connected"...`);

        await db.collection('sessions').doc(session.id).update({
          status: 'connected',
          phone: phone,
          qrCode: null,
          connectedAt: Timestamp.now(),
          lastActivity: Timestamp.now(),
          error: null,
        });

        console.log(`[BRIDGE] Firestore updated successfully!`);

        // Verify the update
        const updatedDoc = await db.collection('sessions').doc(session.id).get();
        const updatedData = updatedDoc.data();
        console.log(`[BRIDGE] Verified status in Firestore: "${updatedData?.status}"`);
      } catch (error) {
        console.error(`[BRIDGE] Error updating session ${session.id}:`, error);
      }
    });

    // Authentication failure
    client.on('auth_failure', async (msg: string) => {
      console.error(`[BRIDGE] ========================================`);
      console.error(`[BRIDGE] AUTH FAILURE for session ${session.id}`);
      console.error(`[BRIDGE] Reason: ${msg}`);
      console.error(`[BRIDGE] ========================================`);

      // Don't update status during graceful shutdown
      if (!this.isShuttingDown) {
        await db.collection('sessions').doc(session.id).update({
          status: 'disconnected',
          error: `Authentication failed: ${msg}`,
          lastActivity: Timestamp.now(),
        });
      }
      this.clients.delete(session.id);
    });

    // Disconnected
    client.on('disconnected', async (reason: string) => {
      console.log(`[BRIDGE] ========================================`);
      console.log(`[BRIDGE] DISCONNECTED session ${session.id}`);
      console.log(`[BRIDGE] Reason: ${reason}`);
      console.log(`[BRIDGE] ========================================`);

      // Don't update status during graceful shutdown (preserve "connected" status)
      if (this.isShuttingDown) {
        console.log(`[BRIDGE] Graceful shutdown - preserving session status`);
      } else {
        await db.collection('sessions').doc(session.id).update({
          status: 'disconnected',
          disconnectedAt: Timestamp.now(),
          lastActivity: Timestamp.now(),
        });
      }
      this.clients.delete(session.id);
    });

    // Remote session saved (important for session persistence)
    client.on('remote_session_saved', () => {
      console.log(`[BRIDGE] Remote session saved for ${session.id}`);
    });

    // Message received - use message_create which fires for both sent and received
    client.on('message_create', async (message: Message) => {
      const direction = message.fromMe ? 'OUTGOING' : 'INCOMING';
      console.log(`[BRIDGE] ${direction} message ${message.fromMe ? 'to' : 'from'} ${message.fromMe ? message.to : message.from}: ${message.body.substring(0, 50)}...`);
      await this.handleMessage(session.id, message);
    });

    // Initialize the client
    console.log(`[BRIDGE] Initializing WhatsApp client...`);
    console.log(`[BRIDGE] Session path: ${sessionPath}`);
    console.log(`[BRIDGE] This may take 30-60 seconds...`);

    const initStartTime = Date.now();

    // Set a timeout to warn if initialization is taking too long
    const initTimeout = setTimeout(() => {
      const elapsed = Math.round((Date.now() - initStartTime) / 1000);
      console.log(`[BRIDGE] WARNING: Initialization taking ${elapsed}s...`);
      console.log(`[BRIDGE] If this continues, try deleting the session folder and restarting`);
    }, 60000);

    try {
      await client.initialize();
      clearTimeout(initTimeout);
      const elapsed = Math.round((Date.now() - initStartTime) / 1000);
      console.log(`[BRIDGE] Client initialized in ${elapsed}s`);
    } catch (error) {
      clearTimeout(initTimeout);
      console.error(`[BRIDGE] ========================================`);
      console.error(`[BRIDGE] INITIALIZATION FAILED for ${session.id}`);
      console.error(`[BRIDGE] Error:`, error);
      console.error(`[BRIDGE] ========================================`);
      await db.collection('sessions').doc(session.id).update({
        status: 'disconnected',
        error: `Initialization failed: ${error}`,
        lastActivity: Timestamp.now(),
      });
      this.clients.delete(session.id);
    }
  }

  /**
   * Extract phone number from WhatsApp ID or contact
   */
  private extractPhoneNumber(waId: string): string {
    // Remove @c.us or @lid suffix and return just the number
    if (waId.includes('@')) {
      return waId.split('@')[0];
    }
    return waId;
  }

  /**
   * Handle WhatsApp message (incoming or outgoing)
   */
  private async handleMessage(sessionId: string, message: Message): Promise<void> {
    const fromRaw = message.from;
    const toRaw = message.to;
    const body = message.body;
    const fromMe = message.fromMe;

    // Try to get contact info for better phone number
    let fromNumber = this.extractPhoneNumber(fromRaw);
    let toNumber = this.extractPhoneNumber(toRaw);

    try {
      const contact = await message.getContact();
      if (contact && contact.number) {
        fromNumber = contact.number;
      }
    } catch {
      // Use extracted number if contact lookup fails
    }

    const direction = fromMe ? 'outgoing' : 'incoming';
    console.log(`[BRIDGE] ${direction} message for session ${sessionId}: ${body.substring(0, 50)}...`);

    // Detect platform
    let platform: 'ifood' | 'rappi' | 'unknown' = 'unknown';
    for (const [p, patterns] of Object.entries(PLATFORM_PATTERNS)) {
      for (const pattern of patterns) {
        if (pattern.test(body) || pattern.test(fromNumber)) {
          platform = p as 'ifood' | 'rappi';
          break;
        }
      }
    }

    // Try to extract OTP
    let otpCode: string | undefined;
    let isOtp = false;
    for (const pattern of OTP_PATTERNS) {
      const match = body.match(pattern);
      if (match && match[1] && match[1].length >= 4 && match[1].length <= 6) {
        otpCode = match[1];
        isOtp = true;
        break;
      }
    }

    // Store message in Firestore
    try {
      await db
        .collection('sessions')
        .doc(sessionId)
        .collection('messages')
        .add({
          sessionId,
          from: fromNumber,
          to: toNumber,
          fromRaw,
          toRaw,
          body,
          fromMe,
          direction,
          timestamp: Timestamp.now(),
          isOtp,
          otpCode: otpCode || null,  // Firestore doesn't accept undefined
          platform,
          read: false,
        });

      // Update session last activity
      await db.collection('sessions').doc(sessionId).update({
        lastActivity: Timestamp.now(),
      });

      if (isOtp) {
        console.log(`[BRIDGE] OTP detected: ${otpCode} from ${platform}`);
      }
    } catch (error) {
      console.error(`[BRIDGE] Failed to store message:`, error);
    }
  }

  /**
   * Stop all clients
   */
  async stop(): Promise<void> {
    this.isShuttingDown = true;
    console.log('[BRIDGE] Stopping all clients (status will be preserved)...');
    for (const [sessionId, client] of this.clients) {
      try {
        await client.destroy();
        console.log(`[BRIDGE] Stopped client for session ${sessionId}`);
      } catch (error) {
        console.error(`[BRIDGE] Error stopping client ${sessionId}:`, error);
      }
    }
    this.clients.clear();
  }
}

// CLI entry point
const bridge = new WhatsAppBridgeFirestore();

// Handle graceful shutdown
process.on('SIGINT', async () => {
  console.log('\n[BRIDGE] Shutting down...');
  await bridge.stop();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.log('\n[BRIDGE] Shutting down...');
  await bridge.stop();
  process.exit(0);
});

// Start the bridge
bridge.start().catch((error) => {
  console.error('[BRIDGE] Fatal error:', error);
  process.exit(1);
});
