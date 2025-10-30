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
        isProcessing: false
    };

    // Onboarding steps
    const onboardingSteps = [
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
            question: 'What industry are you in? (e.g., Technology, Retail, Healthcare, Consulting)',
            field: 'industry',
            required: false
        },
        {
            id: 'complete',
            message: 'Perfect! I\'m creating your tenant now...',
            final: true
        }
    ];

    // DOM elements
    let toggleBtn, closeBtn, botWindow, messagesContainer, inputField, sendBtn, loadingIndicator, progressBar, progressText;

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

    // Start onboarding flow
    function startOnboarding() {
        addBotMessage(onboardingSteps[0].message);
        setTimeout(() => {
            addBotMessage(onboardingSteps[0].question);
            updateProgress();
        }, 1000);
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

        const currentStep = onboardingSteps[botState.currentStep];

        // Save user data
        if (currentStep.field) {
            botState.userData[currentStep.field] = input;
        }

        // Move to next step
        botState.currentStep++;

        // Check if we're done
        if (botState.currentStep >= onboardingSteps.length) {
            await completeTenantSetup();
        } else {
            const nextStep = onboardingSteps[botState.currentStep];

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
                    completeTenantSetup();
                }
            }, 1000);
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

            // Create tenant via API
            const response = await fetch('/api/tenants', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${idToken}`
                },
                body: JSON.stringify({
                    company_name: botState.userData.company_name,
                    description: botState.userData.description || '',
                    industry: botState.userData.industry || ''
                })
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
                        }
                    });

                    if (switchResponse.ok) {
                        addBotMessage('All set! Reloading the page...');
                        setTimeout(() => {
                            window.location.reload();
                        }, 1500);
                    } else {
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
        const percent = customPercent !== undefined ? customPercent :
            Math.round((botState.currentStep / onboardingSteps.length) * 100);

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
