/**
 * TrustChain JavaScript SDK
 * 
 * Provides cryptographically verified tool execution for JavaScript/Node.js applications.
 * 
 * @version 2.0.0
 * @author TrustChain Team
 */

class TrustChainError extends Error {
    constructor(message, code = null, details = null) {
        super(message);
        this.name = 'TrustChainError';
        this.code = code;
        this.details = details;
    }
}

class VerificationError extends TrustChainError {
    constructor(message, signature = null) {
        super(message, 'VERIFICATION_FAILED');
        this.signature = signature;
    }
}

class SignedResponse {
    /**
     * Represents a cryptographically signed tool response.
     */
    constructor(data) {
        this.tool_id = data.tool_id;
        this.data = data.data;
        this.signature = data.signature;
        this.signature_id = data.signature_id || '';
        this.timestamp = data.timestamp || Date.now() / 1000;
        this.nonce = data.nonce || null;
        this.is_verified = data.is_verified || false;
    }

    /**
     * Convert to dictionary for serialization.
     */
    toDict() {
        return {
            tool_id: this.tool_id,
            data: this.data,
            signature: this.signature,
            signature_id: this.signature_id,
            timestamp: this.timestamp,
            nonce: this.nonce,
            is_verified: this.is_verified
        };
    }

    /**
     * Get signature preview (first 16 characters + ...).
     */
    getSignaturePreview() {
        if (!this.signature) return 'No signature';
        return this.signature.substring(0, 16) + '...';
    }

    /**
     * Get human-readable timestamp.
     */
    getFormattedTimestamp() {
        return new Date(this.timestamp * 1000).toISOString();
    }
}

class TrustChainClient {
    /**
     * JavaScript client for TrustChain API.
     * 
     * @param {string} baseUrl - Base URL of TrustChain server
     * @param {Object} options - Configuration options
     */
    constructor(baseUrl = 'http://localhost:8000', options = {}) {
        this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
        this.options = {
            timeout: 30000,
            retries: 3,
            autoVerify: true,
            ...options
        };
        
        // WebSocket connection for real-time updates
        this.websocket = null;
        this.wsCallbacks = new Map();
        
        // Statistics
        this.stats = {
            totalCalls: 0,
            successfulCalls: 0,
            failedCalls: 0,
            verificationSuccess: 0,
            verificationFailed: 0
        };
    }

    /**
     * Call a registered tool on the TrustChain server.
     * 
     * @param {string} toolName - Name of the tool to call
     * @param {Object} parameters - Parameters to pass to the tool
     * @param {string|null} nonce - Optional nonce for replay protection
     * @returns {Promise<SignedResponse>} Signed response from the tool
     */
    async callTool(toolName, parameters = {}, nonce = null) {
        const startTime = Date.now();
        this.stats.totalCalls++;

        try {
            const response = await this._makeRequest('/api/tools/call', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    tool_name: toolName,
                    parameters: parameters,
                    nonce: nonce
                })
            });

            if (!response.success) {
                this.stats.failedCalls++;
                throw new TrustChainError(
                    response.error || 'Tool execution failed',
                    'TOOL_EXECUTION_FAILED',
                    { toolName, parameters }
                );
            }

            const signedResponse = new SignedResponse(response.signed_response);
            this.stats.successfulCalls++;

            // Auto-verify if enabled
            if (this.options.autoVerify) {
                const isValid = await this.verify(signedResponse);
                if (!isValid) {
                    this.stats.verificationFailed++;
                    throw new VerificationError(
                        `Tool response signature verification failed for ${toolName}`,
                        signedResponse.signature
                    );
                }
                this.stats.verificationSuccess++;
            }

            return signedResponse;

        } catch (error) {
            this.stats.failedCalls++;
            if (error instanceof TrustChainError) {
                throw error;
            }
            throw new TrustChainError(
                `Failed to call tool ${toolName}: ${error.message}`,
                'NETWORK_ERROR',
                { toolName, parameters, originalError: error.message }
            );
        }
    }

    /**
     * Verify a signed response.
     * 
     * @param {SignedResponse} signedResponse - Response to verify
     * @returns {Promise<boolean>} True if signature is valid
     */
    async verify(signedResponse) {
        try {
            const response = await this._makeRequest('/api/tools/verify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    signed_response: signedResponse.toDict()
                })
            });

            return response.valid;

        } catch (error) {
            console.warn('Verification request failed:', error.message);
            return false;
        }
    }

    /**
     * Get list of available tools.
     * 
     * @returns {Promise<Array>} List of available tools
     */
    async getTools() {
        try {
            const response = await this._makeRequest('/api/tools');
            return response.tools;
        } catch (error) {
            throw new TrustChainError(
                `Failed to get tools list: ${error.message}`,
                'API_ERROR'
            );
        }
    }

    /**
     * Get TrustChain server statistics.
     * 
     * @returns {Promise<Object>} Server statistics
     */
    async getServerStats() {
        try {
            const response = await this._makeRequest('/api/stats');
            return response;
        } catch (error) {
            throw new TrustChainError(
                `Failed to get server stats: ${error.message}`,
                'API_ERROR'
            );
        }
    }

    /**
     * Get client-side statistics.
     * 
     * @returns {Object} Client statistics
     */
    getClientStats() {
        return {
            ...this.stats,
            successRate: this.stats.totalCalls > 0 
                ? (this.stats.successfulCalls / this.stats.totalCalls * 100).toFixed(2) + '%'
                : 'N/A',
            verificationRate: this.stats.verificationSuccess + this.stats.verificationFailed > 0
                ? (this.stats.verificationSuccess / (this.stats.verificationSuccess + this.stats.verificationFailed) * 100).toFixed(2) + '%'
                : 'N/A'
        };
    }

    /**
     * Check server health.
     * 
     * @returns {Promise<Object>} Health status
     */
    async healthCheck() {
        try {
            const response = await this._makeRequest('/health');
            return response;
        } catch (error) {
            throw new TrustChainError(
                `Health check failed: ${error.message}`,
                'HEALTH_CHECK_FAILED'
            );
        }
    }

    /**
     * Connect to WebSocket for real-time updates.
     * 
     * @param {Function} onMessage - Callback for WebSocket messages
     * @returns {Promise<void>}
     */
    async connectWebSocket(onMessage = null) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            console.warn('WebSocket already connected');
            return;
        }

        const wsUrl = this.baseUrl.replace(/^http/, 'ws') + '/ws';
        
        return new Promise((resolve, reject) => {
            try {
                this.websocket = new WebSocket(wsUrl);
                
                this.websocket.onopen = () => {
                    console.log('Connected to TrustChain WebSocket');
                    resolve();
                };
                
                this.websocket.onmessage = (event) => {
                    try {
                        const message = JSON.parse(event.data);
                        
                        // Call registered callbacks
                        this.wsCallbacks.forEach(callback => {
                            try {
                                callback(message);
                            } catch (error) {
                                console.error('WebSocket callback error:', error);
                            }
                        });
                        
                        // Call provided callback
                        if (onMessage) {
                            onMessage(message);
                        }
                    } catch (error) {
                        console.error('Failed to parse WebSocket message:', error);
                    }
                };
                
                this.websocket.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    reject(new TrustChainError('WebSocket connection failed', 'WEBSOCKET_ERROR'));
                };
                
                this.websocket.onclose = () => {
                    console.log('WebSocket connection closed');
                    this.websocket = null;
                };
                
            } catch (error) {
                reject(new TrustChainError(`Failed to create WebSocket: ${error.message}`, 'WEBSOCKET_ERROR'));
            }
        });
    }

    /**
     * Disconnect WebSocket.
     */
    disconnectWebSocket() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
    }

    /**
     * Register callback for WebSocket messages.
     * 
     * @param {string} id - Callback ID
     * @param {Function} callback - Callback function
     */
    onWebSocketMessage(id, callback) {
        this.wsCallbacks.set(id, callback);
    }

    /**
     * Unregister WebSocket callback.
     * 
     * @param {string} id - Callback ID
     */
    offWebSocketMessage(id) {
        this.wsCallbacks.delete(id);
    }

    /**
     * Make HTTP request with error handling and retries.
     * 
     * @private
     */
    async _makeRequest(endpoint, options = {}) {
        const url = this.baseUrl + endpoint;
        let lastError;

        for (let attempt = 1; attempt <= this.options.retries; attempt++) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), this.options.timeout);

                const response = await fetch(url, {
                    ...options,
                    signal: controller.signal
                });

                clearTimeout(timeoutId);

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                return await response.json();

            } catch (error) {
                lastError = error;
                
                if (attempt < this.options.retries) {
                    // Exponential backoff
                    const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
                    await new Promise(resolve => setTimeout(resolve, delay));
                    continue;
                }
                
                break;
            }
        }

        throw lastError;
    }
}

// Utility functions
const TrustChainUtils = {
    /**
     * Generate a random nonce.
     */
    generateNonce() {
        return 'nonce_' + Math.random().toString(36).substring(2) + '_' + Date.now();
    },

    /**
     * Format execution time.
     */
    formatExecutionTime(ms) {
        if (ms < 1000) {
            return `${ms.toFixed(1)}ms`;
        } else {
            return `${(ms / 1000).toFixed(2)}s`;
        }
    },

    /**
     * Validate tool name.
     */
    validateToolName(name) {
        if (!name || typeof name !== 'string') {
            throw new TrustChainError('Tool name must be a non-empty string');
        }
        if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(name)) {
            throw new TrustChainError('Tool name must start with a letter and contain only letters, numbers, and underscores');
        }
        return true;
    }
};

// Export for different environments
if (typeof module !== 'undefined' && module.exports) {
    // Node.js
    module.exports = {
        TrustChainClient,
        SignedResponse,
        TrustChainError,
        VerificationError,
        TrustChainUtils
    };
} else if (typeof window !== 'undefined') {
    // Browser
    window.TrustChain = {
        TrustChainClient,
        SignedResponse,
        TrustChainError,
        VerificationError,
        TrustChainUtils
    };
} 