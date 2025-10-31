/**
 * Onboarding Bot - Business Setup Assistant
 * Helps CFOs and business owners set up their tenant with AI assistance
 */

(function() {
    'use strict';

    // Bot state
    let botState = {
        isOpen: false,
        currentStep: 0,
        userData: {},
        isProcessing: false,
        mode: null, // 'create_tenant' or 'configure_tenant'
        currentTenant: null,
        awaitingDocumentResponse: false, // Tracking if waiting for yes/no after document upload
        awaitingEntityResponse: false, // Tracking if waiting for yes/no after entity creation
        creatingEntity: false, // Tracking if in entity creation flow
        entityData: {}, // Temporary entity data being collected
        entityStep: 0, // Current step in entity creation (0: name, 1: description, 2: type)
        conversationMode: false, // Tracking if in AI conversation mode
        conversationHistory: [] // Chat history for AI context
    };

    // Steps for creating a NEW tenant
    const createTenantSteps = [
        {
            id: 'welcome',
            message: 'Welcome! I\'m your AI assistant to help set up your business in Delta CFO Agent. Let\'s get started!',
            question: 'What is your company name?',
            field: 'company_name',
            required: true
        },
        {
            id: 'description',
            message: 'Great! Now tell me a bit about your business.',
            question: 'What does your company do? (Brief description)',
            field: 'description',
            required: false
        },
        {
            id: 'industry',
            message: 'Understanding your industry helps me configure the right financial categories.',
            question: 'What industry are you in? (Technology, Retail, Healthcare, Consulting, or Other)',
            field: 'industry',
            required: false
        },
        {
            id: 'chart_of_accounts',
            message: 'Perfect! Now let\'s set up your chart of accounts.',
            question: 'Would you like me to create industry-specific accounting categories? (yes/no)',
            field: 'use_template',
            required: false
        },
        {
            id: 'complete',
            message: 'Perfect! I\'m creating your tenant with all the configurations...',
            final: true
        }
    ];

    // Steps for configuring EXISTING tenant
    const configureTenantSteps = [
        {
            id: 'welcome_existing',
            message: 'Hi! I can help you complete your tenant setup. What would you like to configure?',
            question: 'Choose an option: (1) Add business entities, (2) Add bank accounts, (3) Upload documents, or (4) Exit',
            field: 'configure_option',
            required: true
        },
        {
            id: 'configure_action',
            message: 'Great! Let me help you with that.',
            final: false
        },
        {
            id: 'complete',
            message: 'All done! Your tenant has been updated.',
            final: true
        }
    ];

    // DOM elements
    let toggleBtn, closeBtn, botWindow, messagesContainer, inputField, sendBtn, loadingIndicator, progressBar, progressText, progressContainer;

    // Initialize bot when DOM is ready
    function init() {
        // Get DOM elements
        toggleBtn = document.getElementById('onboardingBotToggle');
        closeBtn = document.getElementById('onboardingBotClose');
        botWindow = document.getElementById('onboardingBotWindow');
        messagesContainer = document.getElementById('onboardingBotMessages');
        inputField = document.getElementById('onboardingBotInput');
        sendBtn = document.getElementById('onboardingBotSend');
        loadingIndicator = document.getElementById('onboardingBotLoading');
        progressBar = document.getElementById('onboardingProgress');
        progressText = document.getElementById('onboardingProgressText');
        progressContainer = document.getElementById('onboardingProgressContainer');

        if (!toggleBtn || !botWindow) {
            console.warn('[OnboardingBot] Required elements not found');
            return;
        }

        // Attach event listeners
        toggleBtn.addEventListener('click', toggleBot);
        closeBtn.addEventListener('click', closeBot);
        sendBtn.addEventListener('click', sendMessage);
        inputField.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        inputField.addEventListener('input', updateSendButton);

        console.log('[OnboardingBot] Initialized successfully');
    }

    // Toggle bot visibility
    function toggleBot() {
        if (botState.isOpen) {
            closeBot();
        } else {
            openBot();
        }
    }

    // Open bot
    function openBot() {
        botState.isOpen = true;
        botWindow.style.display = 'flex';

        // Start onboarding if first time
        if (botState.currentStep === 0 && messagesContainer.children.length === 0) {
            startOnboarding();
        }
    }

    // Close bot
    function closeBot() {
        botState.isOpen = false;
        botWindow.style.display = 'none';
    }

    // Get current tenant from various sources
    async function getCurrentTenant() {
        console.log('[OnboardingBot] Detecting current tenant...');

        // Try to get from global variable (set by tenant context)
        console.log('[OnboardingBot] Checking window.currentTenantId:', window.currentTenantId);
        if (window.currentTenantId && window.currentTenantId !== 'delta') {
            const tenant = { id: window.currentTenantId, name: window.currentTenantName || window.currentTenantId };
            console.log('[OnboardingBot] Found tenant from window:', tenant);
            return tenant;
        }

        // Try to get from account menu or data attributes
        const accountMenu = document.querySelector('[data-current-tenant]');
        console.log('[OnboardingBot] Account menu element:', accountMenu);
        if (accountMenu) {
            const tenantId = accountMenu.getAttribute('data-current-tenant');
            console.log('[OnboardingBot] Tenant ID from data attribute:', tenantId);
            if (tenantId && tenantId !== 'delta') {
                const tenant = { id: tenantId, name: accountMenu.getAttribute('data-tenant-name') || tenantId };
                console.log('[OnboardingBot] Found tenant from DOM:', tenant);
                return tenant;
            }
        }

        // Try to get from API /api/auth/me
        try {
            const auth = window.auth;
            console.log('[OnboardingBot] Firebase auth:', auth);
            if (auth && auth.currentUser) {
                console.log('[OnboardingBot] Firebase user:', auth.currentUser.email);
                const idToken = await auth.currentUser.getIdToken();
                const response = await fetch('/api/auth/me', {
                    headers: { 'Authorization': `Bearer ${idToken}` }
                });
                console.log('[OnboardingBot] API response status:', response.status);
                if (response.ok) {
                    const data = await response.json();
                    console.log('[OnboardingBot] API data:', data);
                    if (data.success && data.current_tenant) {
                        const tenant = data.current_tenant;
                        console.log('[OnboardingBot] Tenant from API:', tenant);
                        if (tenant.id && tenant.id !== 'delta') {
                            return { id: tenant.id, name: tenant.company_name || tenant.id };
                        }
                    }
                }
            }
        } catch (error) {
            console.warn('[OnboardingBot] Error fetching tenant from API:', error);
        }

        console.log('[OnboardingBot] No tenant found - returning null');
        return null;
    }

    // Start onboarding flow
    async function startOnboarding() {
        try {
            // Check if user is already in a tenant
            const tenant = await getCurrentTenant();

            if (tenant && tenant.id) {
                // User is in an existing tenant - configure mode
                botState.mode = 'configure_tenant';
                botState.currentTenant = tenant.id;
                console.log('[OnboardingBot] Configure mode for tenant:', tenant.id);

                addBotMessage(`Welcome! You're currently managing "${tenant.name}".`);
                setTimeout(() => {
                    addBotMessage(configureTenantSteps[0].message);
                    setTimeout(() => {
                        addBotMessage('Choose what you would like to configure:');
                        // Add option buttons
                        const options = [
                            { value: '1', icon: '🏢', label: 'Add Business Entities' },
                            { value: '2', icon: '🏦', label: 'Add Bank Accounts' },
                            { value: '3', icon: '📄', label: 'Upload Documents' },
                            { value: '4', icon: '💬', label: 'Talk About Business' },
                            { value: '5', icon: '✅', label: 'Exit' }
                        ];
                        addOptionButtons(options);
                        updateProgress();
                    }, 800);
                }, 1000);
            } else {
                // User is not in a tenant - create mode
                botState.mode = 'create_tenant';
                console.log('[OnboardingBot] Create tenant mode');

                addBotMessage(createTenantSteps[0].message);
                setTimeout(() => {
                    addBotMessage(createTenantSteps[0].question);
                    updateProgress();
                }, 1000);
            }
        } catch (error) {
            console.error('[OnboardingBot] Error starting onboarding:', error);
            addBotMessage('Welcome! Let me help you get started.');
            setTimeout(() => {
                addBotMessage(createTenantSteps[0].question);
            }, 1000);
        }
    }

    // Add bot message
    function addBotMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chat-message bot-message';
        messageDiv.innerHTML = `
            <div class="message-content">${text}</div>
            <div class="message-time">${getCurrentTime()}</div>
        `;
        messagesContainer.appendChild(messageDiv);
        scrollToBottom();
    }

    // Add option buttons for configure mode
    function addOptionButtons(options) {
        const buttonsDiv = document.createElement('div');
        buttonsDiv.className = 'chat-message bot-message option-buttons-container';

        const buttonsHTML = options.map(option => `
            <button class="option-button" data-option="${option.value}">
                ${option.icon} ${option.label}
            </button>
        `).join('');

        buttonsDiv.innerHTML = `
            <div class="option-buttons">
                ${buttonsHTML}
            </div>
        `;

        messagesContainer.appendChild(buttonsDiv);
        scrollToBottom();

        // Add click listeners to all buttons
        const buttons = buttonsDiv.querySelectorAll('.option-button');
        buttons.forEach(button => {
            button.addEventListener('click', async () => {
                const selectedOption = button.getAttribute('data-option');

                // Disable all buttons after selection
                buttons.forEach(btn => btn.disabled = true);
                button.classList.add('selected');

                // Add user message showing their choice
                addUserMessage(button.textContent.trim());

                // Process the option
                await handleConfigureOption(selectedOption);
            });
        });
    }

    // Add user message
    function addUserMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chat-message user-message';
        messageDiv.innerHTML = `
            <div class="message-content">${text}</div>
            <div class="message-time">${getCurrentTime()}</div>
        `;
        messagesContainer.appendChild(messageDiv);
        scrollToBottom();
    }

    // Add error message
    function addErrorMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'chat-message bot-message error-message';
        messageDiv.innerHTML = `
            <div class="message-content">${text}</div>
            <div class="message-time">${getCurrentTime()}</div>
        `;
        messagesContainer.appendChild(messageDiv);
        scrollToBottom();
    }

    // Send message
    async function sendMessage() {
        if (botState.isProcessing) return;

        const message = inputField.value.trim();
        if (!message) return;

        // Add user message
        addUserMessage(message);
        inputField.value = '';
        updateSendButton();

        // Process message
        await processUserInput(message);
    }

    // Process user input
    async function processUserInput(input) {
        botState.isProcessing = true;
        showLoading(true);

        // Handle AI conversation mode
        if (botState.conversationMode) {
            await handleConversationInput(input);
            return;
        }

        // Handle document upload yes/no response
        if (botState.awaitingDocumentResponse) {
            await handleDocumentUploadResponse(input);
            return;
        }

        // Handle entity creation yes/no response
        if (botState.awaitingEntityResponse) {
            await handleEntityCreationResponse(input);
            return;
        }

        // Handle entity creation flow
        if (botState.creatingEntity) {
            await handleEntityCreationInput(input);
            return;
        }

        // Get the appropriate steps array based on mode
        const steps = botState.mode === 'configure_tenant' ? configureTenantSteps : createTenantSteps;
        const currentStep = steps[botState.currentStep];

        // Save user data
        if (currentStep.field) {
            botState.userData[currentStep.field] = input;
        }

        // Handle configure mode options
        if (botState.mode === 'configure_tenant' && currentStep.id === 'welcome_existing') {
            await handleConfigureOption(input);
            return;
        }

        // Move to next step
        botState.currentStep++;

        // Check if we're done
        if (botState.currentStep >= steps.length) {
            if (botState.mode === 'create_tenant') {
                await completeTenantSetup();
            } else {
                showLoading(false);
                addBotMessage('All done! Anything else you need?');
                botState.isProcessing = false;
            }
        } else {
            const nextStep = steps[botState.currentStep];

            setTimeout(() => {
                showLoading(false);
                addBotMessage(nextStep.message);

                if (!nextStep.final) {
                    setTimeout(() => {
                        addBotMessage(nextStep.question);
                        updateProgress();
                        botState.isProcessing = false;
                    }, 800);
                } else {
                    if (botState.mode === 'create_tenant') {
                        completeTenantSetup();
                    } else {
                        botState.isProcessing = false;
                    }
                }
            }, 1000);
        }
    }

    // Handle document upload yes/no response
    async function handleDocumentUploadResponse(input) {
        const normalizedInput = input.trim().toLowerCase();
        showLoading(false);

        if (normalizedInput === 'yes' || normalizedInput === 'y' || normalizedInput === 'sim' || normalizedInput === 's') {
            // User wants to upload another document
            botState.awaitingDocumentResponse = false;
            addBotMessage('Great! Please upload your next document.');
            setTimeout(() => {
                showDocumentUploadInterface();
            }, 800);
        } else if (normalizedInput === 'no' || normalizedInput === 'n' || normalizedInput === 'não' || normalizedInput === 'nao') {
            // User is done uploading
            botState.awaitingDocumentResponse = false;
            addBotMessage('Perfect! What else would you like to configure?');
            setTimeout(() => {
                addBotMessage('Choose an option:');
                const options = [
                    { value: '1', icon: '🏢', label: 'Add Business Entities' },
                    { value: '2', icon: '🏦', label: 'Add Bank Accounts' },
                    { value: '3', icon: '📄', label: 'Upload Documents' },
                    { value: '4', icon: '💬', label: 'Talk About Business' },
                    { value: '5', icon: '✅', label: 'Exit' }
                ];
                addOptionButtons(options);
                botState.isProcessing = false;
            }, 1000);
        } else {
            // Invalid response
            addBotMessage('I didn\'t understand that. Please answer "yes" or "no".');
            addBotMessage('Would you like to upload another document? (yes/no)');
            botState.isProcessing = false;
        }
    }

    // Handle entity creation yes/no response
    async function handleEntityCreationResponse(input) {
        const normalizedInput = input.trim().toLowerCase();
        showLoading(false);

        if (normalizedInput === 'yes' || normalizedInput === 'y' || normalizedInput === 'sim' || normalizedInput === 's') {
            // User wants to add another entity
            botState.awaitingEntityResponse = false;
            addBotMessage('Great! Let\'s add another entity.');
            setTimeout(() => {
                addBotMessage('What is the name of the entity?');
                botState.creatingEntity = true;
                botState.entityStep = 0;
                botState.entityData = {};
                botState.isProcessing = false;
            }, 800);
        } else if (normalizedInput === 'no' || normalizedInput === 'n' || normalizedInput === 'não' || normalizedInput === 'nao') {
            // User is done creating entities
            botState.awaitingEntityResponse = false;
            addBotMessage('Perfect! What else would you like to configure?');
            setTimeout(() => {
                addBotMessage('Choose an option:');
                const options = [
                    { value: '1', icon: '🏢', label: 'Add Business Entities' },
                    { value: '2', icon: '🏦', label: 'Add Bank Accounts' },
                    { value: '3', icon: '📄', label: 'Upload Documents' },
                    { value: '4', icon: '✅', label: 'Exit' }
                ];
                addOptionButtons(options);
                botState.isProcessing = false;
            }, 1000);
        } else {
            // Invalid response
            addBotMessage('I didn\'t understand that. Please answer "yes" or "no".');
            addBotMessage('Would you like to add another entity? (yes/no)');
            botState.isProcessing = false;
        }
    }

    // Handle entity creation input
    async function handleEntityCreationInput(input) {
        showLoading(false);

        if (botState.entityStep === 0) {
            // Collecting name
            botState.entityData.name = input.trim();
            botState.entityStep = 1;
            addBotMessage(`Perfect! Entity name: "${botState.entityData.name}"`);
            setTimeout(() => {
                addBotMessage('Please provide a brief description for this entity (or type "skip"):');
                botState.isProcessing = false;
            }, 800);
        } else if (botState.entityStep === 1) {
            // Collecting description
            if (input.trim().toLowerCase() === 'skip') {
                botState.entityData.description = '';
            } else {
                botState.entityData.description = input.trim();
            }
            botState.entityStep = 2;
            addBotMessage('Great! Now, what type of entity is this?');
            setTimeout(() => {
                const typeOptions = [
                    { value: 'subsidiary', icon: '🏢', label: 'Subsidiary' },
                    { value: 'division', icon: '🏭', label: 'Division' },
                    { value: 'branch', icon: '🌳', label: 'Branch' },
                    { value: 'other', icon: '📋', label: 'Other' }
                ];
                addOptionButtons(typeOptions);
                botState.isProcessing = false;
            }, 800);
        } else if (botState.entityStep === 2) {
            // Collecting type and creating entity
            botState.entityData.entity_type = input.trim().toLowerCase();

            // Validate type
            const validTypes = ['subsidiary', 'division', 'branch', 'other'];
            if (!validTypes.includes(botState.entityData.entity_type)) {
                botState.entityData.entity_type = 'other';
            }

            showLoading(true);
            addBotMessage('Creating entity...');

            try {
                // Get auth token
                const auth = window.auth;
                if (!auth || !auth.currentUser) {
                    throw new Error('Not authenticated');
                }

                const idToken = await auth.currentUser.getIdToken();

                // Create entity via API
                const response = await fetch('/api/onboarding/entities', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${idToken}`
                    },
                    body: JSON.stringify(botState.entityData)
                });

                const data = await response.json();
                showLoading(false);

                if (data.success) {
                    addBotMessage(`Success! Entity "${botState.entityData.name}" created and will now appear in your filters and classifications.`);

                    // Reset entity creation state
                    botState.creatingEntity = false;
                    botState.entityStep = 0;
                    botState.entityData = {};

                    // Ask if they want to add another
                    setTimeout(() => {
                        addBotMessage('Would you like to add another entity? (yes/no)');
                        botState.awaitingEntityResponse = true;
                        botState.isProcessing = false;
                    }, 1500);
                } else {
                    addBotMessage(`Error: ${data.message || 'Failed to create entity'}`);
                    botState.creatingEntity = false;
                    botState.entityStep = 0;
                    botState.entityData = {};
                    botState.isProcessing = false;
                }
            } catch (error) {
                showLoading(false);
                console.error('Create entity error:', error);
                addBotMessage('Sorry, there was an error creating the entity. Please try again.');
                botState.creatingEntity = false;
                botState.entityStep = 0;
                botState.entityData = {};
                botState.isProcessing = false;
            }
        }
    }

    // Handle AI conversation input
    async function handleConversationInput(input) {
        const normalizedInput = input.trim().toLowerCase();

        // Check if user wants to exit conversation mode
        if (normalizedInput === 'exit' || normalizedInput === 'done' || normalizedInput === 'stop' || normalizedInput === 'menu') {
            botState.conversationMode = false;
            botState.conversationHistory = [];
            showLoading(false);
            addBotMessage('Thanks for sharing! The information you provided will help improve transaction classification.');
            setTimeout(() => {
                addBotMessage('What else would you like to configure?');
                const options = [
                    { value: '1', icon: '🏢', label: 'Add Business Entities' },
                    { value: '2', icon: '🏦', label: 'Add Bank Accounts' },
                    { value: '3', icon: '📄', label: 'Upload Documents' },
                    { value: '4', icon: '💬', label: 'Talk About Business' },
                    { value: '5', icon: '✅', label: 'Exit' }
                ];
                addOptionButtons(options);
                botState.isProcessing = false;
            }, 1000);
            return;
        }

        try {
            const auth = window.auth;
            if (!auth || !auth.currentUser) {
                throw new Error('Not authenticated');
            }

            const idToken = await auth.currentUser.getIdToken();

            // Add user message to history
            botState.conversationHistory.push({
                role: 'user',
                content: input
            });

            // Call chat API
            const response = await fetch('/api/onboarding/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${idToken}`
                },
                body: JSON.stringify({
                    message: input,
                    conversation_history: botState.conversationHistory.slice(-6) // Send last 6 messages
                })
            });

            const data = await response.json();
            showLoading(false);

            if (data.success) {
                // Add AI response to history
                botState.conversationHistory.push({
                    role: 'assistant',
                    content: data.response
                });

                // Display AI response
                addBotMessage(data.response);

                // If knowledge was extracted, show notification
                if (data.knowledge_extracted && data.knowledge_extracted.length > 0) {
                    setTimeout(() => {
                        const knowledgeMsg = `I extracted ${data.knowledge_extracted.length} insight(s) from our conversation that will help improve your transaction classification.`;
                        addBotMessage(knowledgeMsg);
                    }, 1000);
                }

                // After 5 messages, remind user they can exit
                if (botState.conversationHistory.length >= 10) {
                    setTimeout(() => {
                        addBotMessage('(Type "exit" anytime to return to the main menu)');
                    }, 1500);
                }

                botState.isProcessing = false;

            } else {
                addBotMessage(`Error: ${data.message || 'Failed to process message'}`);
                botState.isProcessing = false;
            }

        } catch (error) {
            showLoading(false);
            console.error('Chat error:', error);
            addBotMessage('Sorry, there was an error processing your message. Please try again.');
            botState.isProcessing = false;
        }
    }

    // Handle configuration options for existing tenant
    async function handleConfigureOption(option) {
        const normalizedOption = option.trim().toLowerCase();

        showLoading(false);

        if (normalizedOption === '1' || normalizedOption.includes('entit')) {
            addBotMessage('Perfect! Let\'s add a new business entity.');
            setTimeout(() => {
                addBotMessage('What is the name of the entity?');
                botState.creatingEntity = true;
                botState.entityStep = 0;
                botState.entityData = {};
                botState.isProcessing = false;
            }, 800);
        } else if (normalizedOption === '2' || normalizedOption.includes('bank') || normalizedOption.includes('account')) {
            addBotMessage('Perfect! Let me take you to the Bank Accounts page.');
            setTimeout(() => {
                window.location.href = '/whitelisted-accounts';
            }, 1500);
        } else if (normalizedOption === '3' || normalizedOption.includes('upload') || normalizedOption.includes('document')) {
            addBotMessage('Perfect! Upload your business documents here (contracts, reports, statements, etc.).');
            addBotMessage('I\'ll analyze them with AI to learn about your business and improve transaction classification.');
            setTimeout(() => {
                showDocumentUploadInterface();
            }, 1000);
        } else if (normalizedOption === '4' || normalizedOption.includes('talk') || normalizedOption.includes('conversation') || normalizedOption.includes('chat')) {
            // Start AI conversation mode
            botState.conversationMode = true;
            botState.conversationHistory = [];
            addBotMessage('Great! I\'d love to learn more about your business.');
            setTimeout(() => {
                addBotMessage('Tell me about your company, your vendors, typical expenses, or any financial patterns I should know about.');
                setTimeout(() => {
                    addBotMessage('(Type "exit" anytime to return to the main menu)');
                    botState.isProcessing = false;
                }, 800);
            }, 1000);
        } else if (normalizedOption === '5' || normalizedOption.includes('exit') || normalizedOption.includes('cancel')) {
            addBotMessage('No problem! Feel free to reach out anytime you need help.');
            botState.isProcessing = false;
            setTimeout(() => {
                closeBot();
            }, 1500);
        } else {
            addBotMessage('I didn\'t understand that. Please type 1, 2, 3, 4, or 5.');
            botState.isProcessing = false;
        }
    }

    // Show document upload interface
    function showDocumentUploadInterface() {
        const uploadDiv = document.createElement('div');
        uploadDiv.className = 'chat-message bot-message upload-interface';
        uploadDiv.innerHTML = `
            <div class="upload-container">
                <input type="file" id="documentFileInput" accept=".pdf,.doc,.docx,.txt" style="display: none;">
                <button class="upload-button" onclick="document.getElementById('documentFileInput').click()">
                    Choose File
                </button>
                <div id="fileNameDisplay" style="margin-top: 0.5rem; font-size: 0.9rem; color: #64748b;"></div>
                <select id="documentTypeSelect" style="margin-top: 0.5rem; padding: 0.5rem; border-radius: 4px; border: 1px solid #e2e8f0; width: 100%;">
                    <option value="contract">Contract</option>
                    <option value="report">Business Report</option>
                    <option value="invoice">Invoice</option>
                    <option value="statement">Financial Statement</option>
                    <option value="other">Other</option>
                </select>
                <button class="upload-submit-button" id="submitDocumentBtn" disabled style="margin-top: 0.75rem; width: 100%; padding: 0.75rem; background: linear-gradient(135deg, #3b82f6, #1d4ed8); color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;">
                    Upload & Analyze
                </button>
            </div>
        `;
        messagesContainer.appendChild(uploadDiv);
        scrollToBottom();

        // Add event listeners
        const fileInput = document.getElementById('documentFileInput');
        const fileNameDisplay = document.getElementById('fileNameDisplay');
        const submitBtn = document.getElementById('submitDocumentBtn');

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                const file = e.target.files[0];
                fileNameDisplay.textContent = `Selected: ${file.name}`;
                submitBtn.disabled = false;
            }
        });

        submitBtn.addEventListener('click', () => handleDocumentUpload());
    }

    // Handle document upload and processing
    async function handleDocumentUpload() {
        const fileInput = document.getElementById('documentFileInput');
        const documentType = document.getElementById('documentTypeSelect').value;
        const submitBtn = document.getElementById('submitDocumentBtn');

        if (!fileInput.files || fileInput.files.length === 0) {
            addBotMessage('Please select a file first.');
            return;
        }

        const file = fileInput.files[0];

        // Disable button and show loading
        submitBtn.disabled = true;
        submitBtn.textContent = 'Uploading...';
        addBotMessage(`Uploading "${file.name}"...`);
        showLoading(true);

        try {
            // Get auth token
            const auth = window.auth;
            if (!auth || !auth.currentUser) {
                throw new Error('Not authenticated');
            }

            const idToken = await auth.currentUser.getIdToken();

            // Prepare form data
            const formData = new FormData();
            formData.append('file', file);
            formData.append('document_type', documentType);
            formData.append('process_immediately', 'true');

            // Upload document
            const response = await fetch('/api/onboarding/upload-document', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${idToken}`
                },
                body: formData
            });

            const data = await response.json();

            showLoading(false);

            if (data.success) {
                addBotMessage(`Success! Document "${file.name}" uploaded and analyzed.`);

                if (data.knowledge_extracted && data.knowledge_extracted.length > 0) {
                    addBotMessage(`I've extracted ${data.knowledge_extracted.length} insight(s) about your business from this document.`);
                    addBotMessage('This knowledge will help me better classify your transactions and understand your business patterns.');
                } else {
                    addBotMessage('Document uploaded successfully. Processing in background...');
                }

                // Ask if they want to upload more
                setTimeout(() => {
                    addBotMessage('Would you like to upload another document? (yes/no)');
                    botState.awaitingDocumentResponse = true;
                    botState.isProcessing = false;
                }, 1500);
            } else {
                addBotMessage(`Error: ${data.message || 'Upload failed'}`);
                submitBtn.disabled = false;
                submitBtn.textContent = 'Upload & Analyze';
                botState.isProcessing = false;
            }

        } catch (error) {
            showLoading(false);
            console.error('Upload error:', error);
            addBotMessage('Sorry, there was an error uploading the document. Please try again.');
            submitBtn.disabled = false;
            submitBtn.textContent = 'Upload & Analyze';
            botState.isProcessing = false;
        }
    }

    // Complete tenant setup
    async function completeTenantSetup() {
        try {
            // Get Firebase auth instance - try multiple sources
            let auth = window.auth;

            // If window.auth doesn't exist, try getting from Firebase modules
            if (!auth) {
                console.warn('[OnboardingBot] window.auth not found, waiting for Firebase...');
                // Wait a bit for Firebase to initialize
                await new Promise(resolve => setTimeout(resolve, 1000));
                auth = window.auth;
            }

            if (!auth) {
                throw new Error('Firebase authentication not initialized. Please refresh the page.');
            }

            // Get current user
            const currentUser = auth.currentUser;
            if (!currentUser) {
                throw new Error('You must be logged in to create a tenant. Please log in first.');
            }

            console.log('[OnboardingBot] Getting auth token for user:', currentUser.email);
            const idToken = await currentUser.getIdToken();

            // Prepare onboarding data
            const industry = (botState.userData.industry || '').toLowerCase();
            const useTemplate = (botState.userData.use_template || '').toLowerCase();
            const addAccounts = (botState.userData.add_accounts || '').toLowerCase();

            // Determine which template to use
            let chartOfAccounts = null;
            if (useTemplate === 'yes' || useTemplate === 'y' || useTemplate === 'sim' || useTemplate === 's') {
                const industryMap = {
                    'technology': 'technology',
                    'tech': 'technology',
                    'retail': 'retail',
                    'varejo': 'retail',
                    'healthcare': 'healthcare',
                    'saude': 'healthcare',
                    'consulting': 'consulting',
                    'consultoria': 'consulting'
                };
                const mappedIndustry = industryMap[industry] || 'generic';
                chartOfAccounts = { template: mappedIndustry };
            }

            // Prepare request payload
            const payload = {
                basic_info: {
                    company_name: botState.userData.company_name,
                    description: botState.userData.description || '',
                    industry: botState.userData.industry || ''
                },
                entities: [],
                chart_of_accounts: chartOfAccounts,
                bank_accounts: [],
                crypto_wallets: []
            };

            // Create tenant via enhanced onboarding API
            const response = await fetch('/api/onboarding/complete-setup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${idToken}`
                },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            showLoading(false);

            if (data.success) {
                addBotMessage(`🎉 Success! Your tenant "${data.tenant.company_name}" has been created!`);
                addBotMessage('Switching to your new tenant now...');

                // Switch to new tenant
                setTimeout(async () => {
                    const switchResponse = await fetch(`/api/auth/switch-tenant/${data.tenant.id}`, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${idToken}`
                        },
                        credentials: 'include'  // Ensure cookies are sent and received
                    });

                    if (switchResponse.ok) {
                        const switchData = await switchResponse.json();
                        console.log('[OnboardingBot] Switch successful:', switchData);
                        addBotMessage('All set! Reloading the page...');
                        setTimeout(() => {
                            // Force full page navigation to ensure session cookie is sent
                            window.location.href = '/';
                        }, 1500);
                    } else {
                        const errorData = await switchResponse.json();
                        console.error('[OnboardingBot] Switch failed:', errorData);
                        addBotMessage('Tenant created successfully! Please refresh the page to see it in your account menu.');
                    }
                }, 2000);

                updateProgress(100);
            } else {
                addErrorMessage(`Sorry, there was an error: ${data.message || 'Unknown error'}`);

                // Reset to beginning
                botState.currentStep = 0;
                botState.userData = {};
                setTimeout(() => {
                    addBotMessage('Let\'s try again. What is your company name?');
                }, 2000);
            }
        } catch (error) {
            showLoading(false);
            console.error('[OnboardingBot] Error creating tenant:', error);
            addErrorMessage(`Error: ${error.message}`);

            // Reset
            botState.currentStep = 0;
            botState.userData = {};
            setTimeout(() => {
                addBotMessage('Let\'s try again. What is your company name?');
            }, 2000);
        }

        botState.isProcessing = false;
    }

    // Update progress bar
    function updateProgress(customPercent) {
        // Only show progress bar during tenant creation, not in configure mode
        if (botState.mode === 'configure_tenant') {
            if (progressContainer) {
                progressContainer.style.display = 'none';
            }
            return;
        }

        // Show progress bar in create_tenant mode
        if (progressContainer) {
            progressContainer.style.display = 'block';
        }

        const steps = botState.mode === 'configure_tenant' ? configureTenantSteps : createTenantSteps;
        const percent = customPercent !== undefined ? customPercent :
            Math.round((botState.currentStep / steps.length) * 100);

        progressBar.style.width = `${percent}%`;
        progressText.textContent = `${percent}%`;
    }

    // Show/hide loading indicator
    function showLoading(show) {
        loadingIndicator.style.display = show ? 'block' : 'none';
    }

    // Update send button state
    function updateSendButton() {
        sendBtn.disabled = !inputField.value.trim() || botState.isProcessing;
    }

    // Scroll to bottom of messages
    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Get current time string
    function getCurrentTime() {
        const now = new Date();
        return now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    }

    // Check URL for ?openBot=true parameter
    function checkAutoOpen() {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('openBot') === 'true') {
            // Remove parameter from URL
            const newUrl = window.location.pathname + window.location.hash;
            window.history.replaceState({}, document.title, newUrl);

            // Open bot after a short delay
            setTimeout(() => {
                openBot();
            }, 500);
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            init();
            checkAutoOpen();
        });
    } else {
        init();
        checkAutoOpen();
    }

})();
