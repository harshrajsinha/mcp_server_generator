        let projectData = null;
        let mcpData = null;
        let appConfig = null;

        // Load configuration from backend
        
        function escapeHtml(text) {
            if (!text) return text;
            return text
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

        async function loadConfig() {
            try {
                const response = await fetch('/api/config');
                if (response.ok) {
                    appConfig = await response.json();
                    // Update form fields with config values (if they exist)
                    const projectPathEl = document.getElementById('projectPath');
                    const sourceFileEl = document.getElementById('sourceFile');
                    
                    if (projectPathEl) {
                        projectPathEl.value = appConfig.default_project_path || '';
                    }
                    if (sourceFileEl) {
                        sourceFileEl.value = appConfig.default_source_file || '';
                    }
                    
                    // Update default config
                    selectedProjectConfig.project_path = appConfig.default_project_path || '';
                    selectedProjectConfig.source_file = appConfig.default_source_file || '';
                }
            } catch (error) {
                console.error('Failed to load config:', error);
            }
        }

        // Initialize on page load
        window.addEventListener('DOMContentLoaded', () => {
            // Load configuration first
            loadConfig();
            // Don't auto-scan, show welcome screen first
            // scanProject();
        });

        // Method Selection Functions
        function selectMethod(method) {
            if (method === 'swagger') {
                showSwaggerModal();
            } else if (method === 'codebase') {
                showCodebaseModal();
            } else if (method === 'database') {
                showDatabaseModal();
            }
        }

        function showSwaggerModal() {
            const modalHTML = `
                <div class="input-modal" id="swaggerModal">
                    <div class="input-modal-content" style="max-width: 600px; max-height: 90vh; overflow-y: auto; position: relative;">
                        <button onclick="document.getElementById('swaggerModal').remove()" style="position: absolute; top: 1rem; right: 1rem; background: rgba(255, 255, 255, 0.2); border: none; color: white; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; transition: all 0.3s ease; z-index: 10;" onmouseover="this.style.background='rgba(255, 255, 255, 0.3)'" onmouseout="this.style.background='rgba(255, 255, 255, 0.2)'">
                            <i class="fas fa-times"></i>
                        </button>
                        <h3><i class="fas fa-link"></i> Swagger/OpenAPI Configuration</h3>
                        <p style="color: rgba(255, 255, 255, 0.7); margin-bottom: 1rem;">
                            Import API endpoints from Swagger/OpenAPI specification
                        </p>

                        <div class="input-group">
                            <label>Swagger/OpenAPI URL <span style="color: var(--anthropic-orange);">*</span></label>
                            <input type="url" id="swaggerUrl" placeholder="https://api.example.com/swagger.json" />
                            <small style="color: rgba(255, 255, 255, 0.5); margin-top: 0.5rem; display: block;">
                                Supports: swagger.json, swagger.yaml, openapi.json, openapi.yaml
                            </small>
                        </div>

                        <div class="input-group">
                            <label>API Base URL (Optional)</label>
                            <input type="url" id="baseUrl" placeholder="https://api.example.com" />
                            <small style="color: rgba(255, 255, 255, 0.5); margin-top: 0.5rem; display: block;">
                                Override the base URL from Swagger spec
                            </small>
                        </div>

                        <!-- OAuth Server Configuration -->
                        <div style="background: rgba(139, 92, 246, 0.1); border-left: 3px solid #8B5CF6; padding: 0.6rem 1rem; margin: 1rem 0 0.5rem 0; border-radius: 4px;">
                            <strong style="color: #8B5CF6; font-size: 0.95rem;">OAuth Server (For Remote Deployment)</strong>
                        </div>

                        <div class="input-group">
                            <label style="display: flex; align-items: center; cursor: pointer;">
                                <input type="checkbox" id="enableOAuthSwagger" style="margin-right: 0.5rem; width: auto;" />
                                <span>Enable OAuth 2.1 Authentication</span>
                            </label>
                            <small style="color: rgba(255, 255, 255, 0.5); margin-top: 0.5rem; display: block;">
                                OAuth server will be automatically configured when MCP server is deployed. Client registration happens at runtime.
                            </small>
                        </div>

                        <!-- Authentication Section -->
                        <div style="background: rgba(59, 130, 246, 0.1); border-left: 3px solid #3B82F6; padding: 0.6rem 1rem; margin: 1rem 0 0.5rem 0; border-radius: 4px;">
                            <strong style="color: #3B82F6; font-size: 0.95rem;">Authentication (Optional)</strong>
                        </div>

                        <form autocomplete="off" onsubmit="return false;">
                            <div class="input-group" style="margin-bottom: 0.75rem;">
                                <label>Authentication Type</label>
                                <select id="authType" style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.2); color: white; padding: 0.75rem; border-radius: 8px; width: 100%;">
                                    <option value="none">None</option>
                                    <option value="bearer">Bearer Token</option>
                                    <option value="api_key">API Key</option>
                                    <option value="basic">Basic Auth</option>
                                </select>
                            </div>

                            <div class="input-group" id="authTokenGroup" style="display: none;">
                                <label>Token/API Key</label>
                                <input type="password" id="authToken" placeholder="Enter your token or API key" autocomplete="off" />
                            </div>

                            <div class="input-group" id="authUserGroup" style="display: none;">
                                <label>Username</label>
                                <input type="text" id="authUser" placeholder="Enter username" autocomplete="username" />
                            </div>

                            <div class="input-group" id="authPassGroup" style="display: none;">
                                <label>Password</label>
                                <input type="password" id="authPass" placeholder="Enter password" autocomplete="current-password" />
                            </div>
                        </form>

                        <!-- SSL/TLS Section -->
                        <div style="background: rgba(16, 185, 129, 0.1); border-left: 3px solid var(--success-green); padding: 0.6rem 1rem; margin: 1rem 0 0.5rem 0; border-radius: 4px;">
                            <strong style="color: var(--success-green); font-size: 0.95rem;">SSL/TLS Configuration</strong>
                        </div>

                        <div class="input-group" style="margin-bottom: 0.75rem;">
                            <label style="display: flex; align-items: center; cursor: pointer;">
                                <input type="checkbox" id="verifySsl" checked style="margin-right: 0.5rem; width: auto;" />
                                <span>Verify SSL Certificate</span>
                            </label>
                            <small style="color: rgba(255, 255, 255, 0.5); margin-top: 0.5rem; display: block;">
                                Uncheck only for self-signed certificates in development
                            </small>
                        </div>

                        <div class="input-group">
                            <label>Timeout (seconds)</label>
                            <input type="number" id="requestTimeout" value="30" min="5" max="300" style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.2); color: white; padding: 0.75rem; border-radius: 8px; width: 100%;" />
                            <small style="color: rgba(255, 255, 255, 0.5); margin-top: 0.5rem; display: block;">
                                Request timeout for fetching Swagger spec
                            </small>
                        </div>

                        <!-- Additional Options -->
                        <div style="background: rgba(139, 92, 246, 0.1); border-left: 3px solid #8B5CF6; padding: 0.6rem 1rem; margin: 1rem 0 0.5rem 0; border-radius: 4px;">
                            <strong style="color: #8B5CF6; font-size: 0.95rem;">Additional Options</strong>
                        </div>

                        <div class="input-group">
                            <label>API Name/Description</label>
                            <input type="text" id="apiName" placeholder="My API Service" />
                            <small style="color: rgba(255, 255, 255, 0.5); margin-top: 0.5rem; display: block;">
                                Optional name to identify this API in MCP Studio
                            </small>
                        </div>

                        <div class="input-buttons">
                            <button class="btn-secondary-custom" onclick="closeSwaggerModal()">
                                <i class="fas fa-times"></i> Cancel
                            </button>
                            <button class="btn-primary-custom" onclick="importFromSwagger()">
                                <i class="fas fa-download"></i> Import APIs
                            </button>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHTML);

            // Add event listener for auth type change
            document.getElementById('authType').addEventListener('change', function () {
                const authType = this.value;
                const tokenGroup = document.getElementById('authTokenGroup');
                const userGroup = document.getElementById('authUserGroup');
                const passGroup = document.getElementById('authPassGroup');

                // Hide all auth fields first
                tokenGroup.style.display = 'none';
                userGroup.style.display = 'none';
                passGroup.style.display = 'none';

                // Show relevant fields based on auth type
                if (authType === 'bearer' || authType === 'api_key') {
                    tokenGroup.style.display = 'block';
                } else if (authType === 'basic') {
                    userGroup.style.display = 'block';
                    passGroup.style.display = 'block';
                }
            });
        }

        // OAuth fields are auto-configured at runtime, no manual toggle needed

        function closeSwaggerModal() {
            const modal = document.getElementById('swaggerModal');
            if (modal) modal.remove();
        }

        function showCodebaseModal() {
            const modalHTML = `
                <div class="input-modal" id="codebaseModal">
                    <div class="input-modal-content" style="max-width: 600px; max-height: 90vh; overflow-y: auto; position: relative;">
                        <button onclick="document.getElementById('codebaseModal').remove()" style="position: absolute; top: 1rem; right: 1rem; background: rgba(255, 255, 255, 0.2); border: none; color: white; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; transition: all 0.3s ease; z-index: 10;" onmouseover="this.style.background='rgba(255, 255, 255, 0.3)'" onmouseout="this.style.background='rgba(255, 255, 255, 0.2)'">
                            <i class="fas fa-times"></i>
                        </button>
                        <h3><i class="fas fa-folder-open"></i> Browse Codebase</h3>
                        <p style="color: rgba(255, 255, 255, 0.7); margin-bottom: 1.5rem;">
                            Scan your local project or GitHub repository for API endpoints
                        </p>

                        <!-- Source Type Selection -->
                        <div style="background: rgba(255, 111, 0, 0.1); border-left: 3px solid var(--anthropic-orange); padding: 1rem; margin-bottom: 1.5rem; border-radius: 4px;">
                            <strong style="color: var(--anthropic-orange);">Source Type</strong>
                        </div>

                        <div class="input-group">
                            <label>Codebase Source</label>
                            <select id="codebaseSourceType" style="background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.2); color: white; padding: 0.75rem; border-radius: 8px; width: 100%;" onchange="toggleCodebaseSource()">
                                <option value="local">Local Folder</option>
                                <option value="github">GitHub Repository</option>
                            </select>
                        </div>

                        <!-- Local Path Fields -->
                        <div id="localPathFields">
                            <div class="input-group">
                                <label>Project Path <span style="color: var(--anthropic-orange);">*</span></label>
                                <input type="text" id="projectPath" placeholder="C:/demo/my-api-project or /path/to/project" value="" />
                                <small style="color: rgba(255, 255, 255, 0.5); margin-top: 0.5rem; display: block;">
                                    Full path to your local project folder
                                </small>
                            </div>
                        </div>

                        <!-- GitHub Fields -->
                        <div id="githubFields" style="display: none;">
                            <div class="input-group">
                                <label>GitHub Repository URL <span style="color: var(--anthropic-orange);">*</span></label>
                                <input type="text" id="githubRepoUrl" placeholder="https://github.com/owner/repo" />
                                <small style="color: rgba(255, 255, 255, 0.5); margin-top: 0.5rem; display: block;">
                                    Full GitHub repository URL
                                </small>
                            </div>
                            <div class="input-group">
                                <label>Branch (Optional)</label>
                                <input type="text" id="githubBranch" placeholder="main" value="main" />
                                <small style="color: rgba(255, 255, 255, 0.5); margin-top: 0.5rem; display: block;">
                                    Repository branch to scan
                                </small>
                            </div>
                            <div class="input-group">
                                <label>GitHub Token (For Private Repos)</label>
                                <input type="password" id="githubToken" placeholder="ghp_..." />
                                <small style="color: rgba(255, 255, 255, 0.5); margin-top: 0.5rem; display: block;">
                                    Optional: Personal access token for private repositories
                                </small>
                            </div>
                        </div>

                        <div class="input-group">
                            <label>Source File (Optional)</label>
                            <input type="text" id="sourceFile" placeholder="app.py or routes.py" value="" />
                            <small style="color: rgba(255, 255, 255, 0.5); margin-top: 0.5rem; display: block;">
                                Leave empty to scan all files
                            </small>
                        </div>
                        <div class="input-group">
                            <label>API Server URL</label>
                            <input type="text" id="apiServerUrl" placeholder="http://localhost:9321" value="http://localhost:9321" />
                            <small style="color: rgba(255, 255, 255, 0.5); margin-top: 0.5rem; display: block;">
                                Base URL where your API server is running (used in generated MCP tools)
                            </small>
                        </div>

                        <!-- OAuth Server Configuration -->
                        <div style="background: rgba(139, 92, 246, 0.1); border-left: 3px solid #8B5CF6; padding: 0.6rem 1rem; margin: 1rem 0 0.5rem 0; border-radius: 4px;">
                            <strong style="color: #8B5CF6; font-size: 0.95rem;">OAuth Server (For Remote Deployment)</strong>
                        </div>

                        <div class="input-group">
                            <label style="display: flex; align-items: center; cursor: pointer;">
                                <input type="checkbox" id="enableOAuthCodebase" style="margin-right: 0.5rem; width: auto;" />
                                <span>Enable OAuth 2.1 Authentication</span>
                            </label>
                            <small style="color: rgba(255, 255, 255, 0.5); margin-top: 0.5rem; display: block;">
                                OAuth server will be automatically configured when MCP server is deployed. Client registration happens at runtime.
                            </small>
                        </div>
                        <div class="input-buttons">
                            <button class="btn-secondary-custom" onclick="closeCodebaseModal()">
                                <i class="fas fa-times"></i> Cancel
                            </button>
                            <button class="btn-primary-custom" onclick="scanFromCodebase()">
                                <i class="fas fa-search"></i> Scan Project
                            </button>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHTML);
        }

        function toggleCodebaseSource() {
            const sourceType = document.getElementById('codebaseSourceType').value;
            const localFields = document.getElementById('localPathFields');
            const githubFields = document.getElementById('githubFields');
            
            if (sourceType === 'github') {
                localFields.style.display = 'none';
                githubFields.style.display = 'block';
            } else {
                localFields.style.display = 'block';
                githubFields.style.display = 'none';
            }
        }

        // OAuth fields are auto-configured at runtime, no manual toggle needed

        function closeCodebaseModal() {
            const modal = document.getElementById('codebaseModal');
            if (modal) modal.remove();
        }

        function showDatabaseModal() {
            const modalHTML = `
                <div class="input-modal" id="databaseModal">
                    <div class="input-modal-content" style="max-width: 800px; max-height: 90vh; overflow-y: auto; position: relative;">
                        <button onclick="document.getElementById('databaseModal').remove()" style="position: absolute; top: 1rem; right: 1rem; background: rgba(255, 255, 255, 0.2); border: none; color: white; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; transition: all 0.3s ease; z-index: 10;" onmouseover="this.style.background='rgba(255, 255, 255, 0.3)'" onmouseout="this.style.background='rgba(255, 255, 255, 0.2)'">
                            <i class="fas fa-times"></i>
                        </button>
                        <h3><i class="fas fa-database"></i> Database MCP Server Configuration</h3>
                        <p style="color: rgba(255, 255, 255, 0.7); margin-bottom: 1.5rem;">
                            Configure database connections for your MCP server. You can add multiple databases and the server will provide tools to interact with them through Claude.
                        </p>
                        
                        <!-- Server Configuration -->
                        <div style="background: rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 1rem; margin-bottom: 1.5rem;">
                            <h4 style="margin-bottom: 1rem; color: var(--scikiq-light-blue);">
                                <i class="fas fa-cog"></i> Server Configuration
                            </h4>
                            <div class="input-group">
                                <label>Server Name</label>
                                <input type="text" id="dbServerName" placeholder="database-mcp-server" value="database-mcp-server" />
                                <small style="color: rgba(255, 255, 255, 0.5); margin-top: 0.5rem; display: block;">
                                    Used as identifier in Claude Desktop configuration
                                </small>
                            </div>
                            <div class="input-group">
                                <label>Server Path</label>
                                <input type="text" id="dbServerPath" placeholder="C:/path/to/dbhandler_mcpserver" value="C:/DAAS/MCP POC/gaurav/dbhandler_mcpserver/scikiq_pkg_dbutils" />
                                <small style="color: rgba(255, 255, 255, 0.5); margin-top: 0.5rem; display: block;">
                                    Path to the database MCP server codebase
                                </small>
                            </div>
                        </div>

                        <!-- Database Connections -->
                        <div style="background: rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 1rem; margin-bottom: 1.5rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                                <h4 style="margin: 0; color: var(--scikiq-light-blue);">
                                    <i class="fas fa-plug"></i> Database Connections
                                </h4>
                                <button onclick="addDatabaseConnection()" style="background: var(--scikiq-light-blue); border: none; color: white; padding: 0.5rem 1rem; border-radius: 4px; cursor: pointer; font-size: 0.9rem;">
                                    <i class="fas fa-plus"></i> Add Database
                                </button>
                            </div>
                            <div id="databaseConnections">
                                <!-- Database connections will be added here -->
                            </div>
                        </div>

                        <div class="input-buttons">
                            <button class="btn-secondary-custom" onclick="closeDatabaseModal()">
                                Cancel
                            </button>
                            <button class="btn-primary-custom" onclick="generateDatabaseMCP()">
                                <i class="fas fa-rocket"></i> Generate & Deploy MCP Server
                            </button>
                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHTML);

            // Add initial database connection
            addDatabaseConnection();
        }

        function closeDatabaseModal() {
            const modal = document.getElementById('databaseModal');
            if (modal) modal.remove();
        }

        let dbConnectionCounter = 0;

        function addDatabaseConnection() {
            dbConnectionCounter++;
            const connectionId = 'db_connection_' + dbConnectionCounter;

            const connectionHTML = `
                <div class="database-connection" id="${connectionId}" style="border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 8px; padding: 1rem; margin-bottom: 1rem; position: relative;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                        <h5 style="margin: 0; color: var(--scikiq-green);">Connection ${dbConnectionCounter}</h5>
                        <button onclick="removeDatabaseConnection('${connectionId}')" style="background: #EF4444; border: none; color: white; padding: 0.3rem 0.6rem; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                        <div class="input-group">
                            <label>Connection Name</label>
                            <input type="text" name="connection_name" placeholder="prod_mysql" value="connection_${dbConnectionCounter}" />
                           
                        </div>
                        <div class="input-group">
                            <label>Database Type</label>
                            <select name="db_type" onchange="updateDatabaseTypeFields('${connectionId}', this.value)">
                                <option value="MYSQL">MySQL</option>
                                <option value="VERTICA">VERTICA</option>
                                <option value="POSTGRES">PostgreSQL</option>
                                <option value="SQLSERVER">SQL Server</option>
                                <option value="ORACLE">Oracle</option>
                                <option value="MONGODB">MongoDB</option>
                                <option value="SNOWFLAKE">Snowflake</option>
                                <option value="REDSHIFT">AWS Redshift</option>
                                <option value="BIGQUERY">Google BigQuery</option>
                                <option value="DUCKDB">DuckDB (Local/S3)</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="database-fields" id="${connectionId}_fields">
                        <!-- Dynamic fields based on database type will be inserted here -->
                    </div>
                </div>
            `;

            document.getElementById('databaseConnections').insertAdjacentHTML('beforeend', connectionHTML);
            updateDatabaseTypeFields(connectionId, 'MYSQL'); // Default to MySQL
        }

        function removeDatabaseConnection(connectionId) {
            const connection = document.getElementById(connectionId);
            if (connection) {
                connection.remove();
            }
        }

        function updateDatabaseTypeFields(connectionId, dbType) {
            const fieldsContainer = document.getElementById(connectionId + '_fields');
            let fieldsHTML = '';

            // Common fields for most databases
            const commonFields = `
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 1rem;">
                    <div class="input-group">
                        <label>Host</label>
                        <input type="text" name="host" placeholder="localhost" value="localhost" />
                    </div>
                    <div class="input-group">
                        <label>Port</label>
                        <input type="number" name="port" placeholder="${getDefaultPort(dbType)}" value="${getDefaultPort(dbType)}" />
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <div class="input-group">
                        <label>Database</label>
                        <input type="text" name="database" placeholder="${getDatabasePlaceholder(dbType)}" />
                    </div>
                    <div class="input-group">
                        <label>Username</label>
                        <input type="text" name="username" placeholder="username" />
                    </div>
                </div>
                <div class="input-group">
                    <label>Password</label>
                    <input type="password" name="password" placeholder="password" />
                </div>
            `;

            fieldsHTML = commonFields;

            // Add database-specific fields
            if (dbType === 'MONGODB') {
                fieldsHTML += `
                    <div class="input-group">
                        <label>Authentication Database</label>
                        <input type="text" name="auth_database" placeholder="admin" value="admin" />
                    </div>
                `;
            } else if (dbType === 'ORACLE') {
                fieldsHTML += `
                    <div class="input-group">
                        <label>Service Name / SID</label>
                        <input type="text" name="service_name" placeholder="ORCL" />
                    </div>
                `;
            } else if (dbType === 'DUCKDB') {
                fieldsHTML = `
                    <div style="background: rgba(0, 163, 224, 0.1); border-left: 4px solid var(--scikiq-light-blue); padding: 1rem; margin-top: 1rem; border-radius: 8px;">
                        <h5 style="margin: 0 0 1rem; color: var(--scikiq-light-blue);">
                            <i class="fas fa-info-circle"></i> DuckDB Configuration
                        </h5>
                        <p style="margin: 0 0 1rem; color: rgba(255, 255, 255, 0.8); font-size: 0.9rem;">
                            DuckDB can work with local files or S3 data sources. Choose your configuration below.
                        </p>
                        
                        <div class="input-group">
                            <label>Connection Type</label>
                            <select name="duckdb_connection_type" onchange="updateDuckDBConnectionType('${connectionId}', this.value)">
                                <option value="local">Local Database File</option>
                                <option value="s3">S3 Data Source</option>
                            </select>
                        </div>
                        
                        <div id="${connectionId}_duckdb_fields">
                            <!-- Dynamic DuckDB fields will be inserted here -->
                        </div>
                    </div>
                `;
            }

            // Add Schema field for VERTICA, POSTGRES, and SQLSERVER
            if (['VERTICA', 'POSTGRES', 'SQLSERVER'].includes(dbType)) {
                fieldsHTML += `
                    <div class="input-group" style="margin-top: 1rem;">
                        <label>Schema <span style="color: rgba(255, 255, 255, 0.5); font-size: 0.85rem;">(Optional)</span></label>
                        <input type="text" name="schema" placeholder="${getDefaultSchema(dbType)}" value="${getDefaultSchema(dbType)}" />
                        <small style="color: rgba(255, 255, 255, 0.5); margin-top: 0.5rem; display: block;">
                            ${dbType === 'VERTICA' ? 'Vertica schema name (default: public)' :
                              dbType === 'POSTGRES' ? 'PostgreSQL schema name (default: public)' :
                              'SQL Server schema name (default: dbo)'}
                        </small>
                    </div>
                `;
            }

            // Add SSL/Security options for applicable databases
            if (['POSTGRES', 'MYSQL', 'SQLSERVER', 'VERTICA'].includes(dbType)) {
                fieldsHTML += `
                    <details style="margin-top: 1rem;">
                        <summary style="cursor: pointer; color: var(--scikiq-light-blue); margin-bottom: 0.5rem;">
                            <i class="fas fa-lock"></i> SSL/Security Options (Optional)
                        </summary>
                        <div style="background: rgba(255, 255, 255, 0.03); padding: 1rem; border-radius: 4px;">
                            <div class="input-group">
                                <label>SSL Mode</label>
                                <select name="ssl_mode">
                                    <option value="">None</option>
                                    <option value="require">Require</option>
                                    <option value="prefer">Prefer</option>
                                    <option value="disable">Disable</option>
                                </select>
                            </div>
                        </div>
                    </details>
                `;
            }

            fieldsContainer.innerHTML = fieldsHTML;

            // Initialize DuckDB fields if it's DuckDB
            if (dbType === 'DUCKDB') {
                setTimeout(() => updateDuckDBConnectionType(connectionId, 'local'), 100);
            }
        }

        function updateDuckDBConnectionType(connectionId, connectionType) {
            const duckdbFieldsContainer = document.getElementById(connectionId + '_duckdb_fields');
            let fieldsHTML = '';

            if (connectionType === 'local') {
                fieldsHTML = `
                    <div class="input-group">
                        <label>Database Path</label>
                        <input type="text" name="database_path" placeholder="/path/to/database.duckdb" />
                        <small style="color: rgba(255, 255, 255, 0.5); margin-top: 0.5rem; display: block;">
                            Path to DuckDB file (leave empty for in-memory database)
                        </small>
                    </div>
                `;
            } else if (connectionType === 's3') {
                fieldsHTML = `
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                        <div class="input-group">
                            <label>AWS Access Key ID</label>
                            <input type="text" name="aws_access_key_id" placeholder="AKIAIOSFODNN7EXAMPLE" />
                        </div>
                        <div class="input-group">
                            <label>AWS Secret Access Key</label>
                            <input type="password" name="aws_secret_access_key" placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" />
                        </div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                        <div class="input-group">
                            <label>AWS Region</label>
                            <select name="region_name">
                                <option value="us-east-1">US East (N. Virginia)</option>
                                <option value="us-west-2">US West (Oregon)</option>
                                <option value="ap-south-1" selected>Asia Pacific (Mumbai)</option>
                                <option value="ap-southeast-1">Asia Pacific (Singapore)</option>
                                <option value="ap-southeast-2">Asia Pacific (Sydney)</option>
                                <option value="eu-west-1">Europe (Ireland)</option>
                                <option value="eu-central-1">Europe (Frankfurt)</option>
                            </select>
                        </div>
                        <div class="input-group">
                            <label>S3 Bucket Name</label>
                            <input type="text" name="bucket_name" placeholder="my-data-bucket" />
                        </div>
                    </div>
                    <div style="background: rgba(255, 193, 7, 0.1); border-left: 4px solid #FFC107; padding: 0.8rem; margin-top: 1rem; border-radius: 4px;">
                        <div style="display: flex; align-items: start; gap: 0.5rem;">
                            <i class="fas fa-exclamation-triangle" style="color: #FFC107; margin-top: 0.2rem;"></i>
                            <div>
                                <strong style="color: #FFC107;">S3 Configuration Note:</strong>
                                <p style="margin: 0.3rem 0 0; color: rgba(255, 255, 255, 0.8); font-size: 0.85rem;">
                                    DuckDB will use these credentials to read data directly from S3. Ensure your AWS credentials have appropriate S3 read permissions for the specified bucket.
                                </p>
                            </div>
                        </div>
                    </div>
                `;
            }

            if (duckdbFieldsContainer) {
                duckdbFieldsContainer.innerHTML = fieldsHTML;
            }
        }

        function getDefaultPort(dbType) {
            const ports = {
                'MYSQL': 3306,
                'POSTGRES': 5432,
                'SQLSERVER': 1433,
                'ORACLE': 1521,
                'MONGODB': 27017,
                'SNOWFLAKE': 443,
                'REDSHIFT': 5439,
                'BIGQUERY': 443,
                'DUCKDB': '',
                'VERTICA': 5433
            };
            return ports[dbType] || '';
        }

        function getDatabasePlaceholder(dbType) {
            const placeholders = {
                'MYSQL': 'database_name',
                'POSTGRES': 'database_name',
                'SQLSERVER': 'master',
                'ORACLE': 'ORCL',
                'MONGODB': 'database_name',
                'SNOWFLAKE': 'database_name',
                'REDSHIFT': 'database_name',
                'BIGQUERY': 'project_id',
                'DUCKDB': 'memory',
                'VERTICA': 'database_name'
            };
            return placeholders[dbType] || 'database_name';
        }

        function getDefaultSchema(dbType) {
            const schemas = {
                'VERTICA': 'public',
                'POSTGRES': 'public',
                'SQLSERVER': 'dbo'
            };
            return schemas[dbType] || '';
        }

        async function generateDatabaseMCP() {
            try {
                // Collect server configuration
                const serverName = document.getElementById('dbServerName').value;
                const serverPath = document.getElementById('dbServerPath').value;

                if (!serverName || !serverPath) {
                    alert('Please provide server name and path');
                    return;
                }

                // Collect database connections
                const connections = [];
                const connectionElements = document.querySelectorAll('.database-connection');

                for (let connectionEl of connectionElements) {
                    const connection = {};

                    // Get all input fields in this connection
                    const inputs = connectionEl.querySelectorAll('input, select');
                    for (let input of inputs) {
                        if (input.value) {
                            connection[input.name] = input.value;
                        }
                    }

                    // Validate required fields
                    if (!connection.connection_name || !connection.db_type) {
                        alert('Please fill in all required fields for all connections');
                        return;
                    }

                    connections.push(connection);
                }

                if (connections.length === 0) {
                    alert('Please add at least one database connection');
                    return;
                }

                // Show loading
                const button = event.target;
                const originalText = button.innerHTML;
                button.innerHTML = '<div class="loading-spinner"></div> Generating...';
                button.disabled = true;

                // Send to backend to generate config.ini and deploy
                const response = await fetch('/api/generate-database-mcp', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        server_name: serverName,
                        server_path: serverPath,
                        connections: connections
                    })
                });

                const result = await response.json();

                if (result.success) {
                    // Close the modal
                    closeDatabaseModal();

                    // Show success modal with deployment information
                    showDatabaseMCPSetupModal(result);
                } else {
                    throw new Error(result.error || 'Failed to generate database MCP server');
                }

            } catch (error) {
                console.error('Error generating database MCP:', error);
                alert('Error: ' + error.message);
            } finally {
                // Reset button
                const button = event.target;
                if (button) {
                    button.innerHTML = originalText;
                    button.disabled = false;
                }
            }
        }

        function showDatabaseMCPSetupModal(result) {
            const configPath = result.config_path;
            const serverPath = result.server_path;
            const pythonPath = result.python_path || 'python';
            const serverName = result.server_name;

            // Ensure proper Windows path formatting for display
            const normalizedConfigPath = configPath.replace(/\//g, '\\');
            const normalizedServerPath = serverPath.replace(/\//g, '\\');

            const modalHTML = `
                <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.8); z-index: 10000; display: flex; align-items: center; justify-content: center; padding: 2rem;">
                    <div style="background: linear-gradient(135deg, var(--dark-bg), #1a1f3a); border: 2px solid var(--scikiq-light-blue); border-radius: 16px; max-width: 900px; width: 100%; max-height: 90vh; overflow-y: auto; position: relative;">
                        
                        <!-- Header -->
                        <div style="background: linear-gradient(135deg, var(--scikiq-light-blue), var(--scikiq-green)); padding: 2rem; text-align: center; border-radius: 14px 14px 0 0; position: relative;">
                            <button onclick="this.closest('[style*=fixed]').remove()" style="position: absolute; top: 1rem; right: 1rem; background: rgba(255, 255, 255, 0.2); border: none; color: white; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; transition: all 0.3s ease;" onmouseover="this.style.background='rgba(255, 255, 255, 0.3)'" onmouseout="this.style.background='rgba(255, 255, 255, 0.2)'">
                                <i class="fas fa-times"></i>
                            </button>
                            <i class="fas fa-database" style="font-size: 3rem; margin-bottom: 1rem; color: white;"></i>
                            <h2 style="margin: 0; color: white; font-family: 'Space Grotesk', sans-serif;">
                                Database MCP Server Ready!
                            </h2>
                            <p style="margin: 0.5rem 0 0; color: rgba(255, 255, 255, 0.9); font-size: 1.1rem;">
                                Your database MCP server has been configured and is ready for deployment
                            </p>
                        </div>

                        <div style="padding: 2rem;">

                            <!-- Deployment Method Selection -->
                            <div style="margin-bottom: 2rem;">
                                <h4 style="color: var(--scikiq-light-blue); margin-bottom: 1rem;">
                                    <i class="fas fa-rocket"></i> Choose Deployment Method
                                </h4>
                                
                                <!-- Deployment Method Tabs -->
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem;">
                                    <button onclick="switchDeploymentMethod('local')" class="deploy-method-btn" data-method="local" style="padding: 1.5rem; background: linear-gradient(135deg, var(--scikiq-light-blue), #0891B2); border: 3px solid var(--scikiq-light-blue); border-radius: 12px; color: white; cursor: pointer; transition: all 0.3s; text-align: left;">
                                        <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 0.5rem;">
                                            <i class="fas fa-desktop" style="font-size: 1.5rem;"></i>
                                            <strong style="font-size: 1.1rem;">Local Installation</strong>
                                        </div>
                                        <p style="margin: 0; font-size: 0.85rem; opacity: 0.9;">Install on this machine's Claude Desktop</p>
                                    </button>
                                    
                                    <button onclick="switchDeploymentMethod('online')" class="deploy-method-btn" data-method="online" style="padding: 1.5rem; background: rgba(124, 58, 237, 0.2); border: 3px solid transparent; border-radius: 12px; color: white; cursor: pointer; transition: all 0.3s; text-align: left;">
                                        <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 0.5rem;">
                                            <i class="fas fa-cloud" style="font-size: 1.5rem;"></i>
                                            <strong style="font-size: 1.1rem;">Online Deployment</strong>
                                        </div>
                                        <p style="margin: 0; font-size: 0.85rem; opacity: 0.9;">Deploy to AWS, Azure, or Remote Server</p>
                                    </button>
                                </div>

                                <!-- Local Deployment Content -->
                                <div id="local-deployment-content" class="deployment-content" style="display: block;">
                                    <div style="background: rgba(0, 163, 224, 0.1); border-left: 4px solid var(--scikiq-light-blue); padding: 1.5rem; border-radius: 8px;">
                                        <h5 style="margin: 0 0 0.5rem; color: var(--scikiq-light-blue);">
                                            <i class="fas fa-magic"></i> Automatic Deployment (Recommended)
                                        </h5>
                                        <p style="margin: 0 0 1rem; color: rgba(255, 255, 255, 0.8);">
                                            We can automatically add this server to your Claude Desktop configuration.
                                        </p>
                                        <button onclick="autoDeployDatabaseMCP('${configPath}', '${serverPath}', '${serverName}')" style="background: var(--scikiq-light-blue); border: none; color: white; padding: 0.8rem 1.5rem; border-radius: 6px; cursor: pointer; font-weight: 600;">
                                            <i class="fas fa-rocket"></i> Auto-Deploy to Claude Desktop
                                        </button>
                                    </div>
                                </div>

                                <!-- Online Deployment Content -->
                                <div id="online-deployment-content" class="deployment-content" style="display: none;">
                                    <!-- Online Deployment Tabs -->
                                    <div style="display: flex; gap: 0.5rem; margin-bottom: 1.5rem; border-bottom: 2px solid rgba(255, 255, 255, 0.1);">
                                        <button onclick="switchOnlineDeployTab('aws')" class="online-deploy-tab active" data-tab="aws" style="flex: 1; padding: 0.8rem; background: transparent; border: none; border-bottom: 3px solid var(--anthropic-orange); color: var(--anthropic-orange); cursor: pointer; transition: all 0.3s; font-weight: 600;">
                                            <i class="fab fa-aws"></i> AWS EC2
                                        </button>
                                        <button onclick="switchOnlineDeployTab('azure')" class="online-deploy-tab" data-tab="azure" style="flex: 1; padding: 0.8rem; background: transparent; border: none; border-bottom: 3px solid transparent; color: rgba(255, 255, 255, 0.6); cursor: pointer; transition: all 0.3s; font-weight: 600;">
                                            <i class="fab fa-microsoft"></i> Azure VM
                                        </button>
                                        <button onclick="switchOnlineDeployTab('remote')" class="online-deploy-tab" data-tab="remote" style="flex: 1; padding: 0.8rem; background: transparent; border: none; border-bottom: 3px solid transparent; color: rgba(255, 255, 255, 0.6); cursor: pointer; transition: all 0.3s; font-weight: 600;">
                                            <i class="fas fa-server"></i> Remote SSH
                                        </button>
                                    </div>

                                    <!-- AWS Tab Content -->
                                    <div id="aws-online-tab" class="online-tab-content" style="display: block;">
                                        <div class="input-group" style="margin-bottom: 1rem;">
                                            <label>AWS Access Key <span style="color: var(--anthropic-orange);">*</span></label>
                                            <input type="text" id="dbAwsAccessKey" placeholder="AKIA..." style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 8px; padding: 0.8rem; color: white; width: 100%;" />
                                        </div>
                                        <div class="input-group" style="margin-bottom: 1rem;">
                                            <label>AWS Secret Key <span style="color: var(--anthropic-orange);">*</span></label>
                                            <input type="password" id="dbAwsSecretKey" placeholder="Secret access key" style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 8px; padding: 0.8rem; color: white; width: 100%;" />
                                        </div>
                                        <div class="input-group" style="margin-bottom: 1rem;">
                                            <label>AWS Region <span style="color: var(--anthropic-orange);">*</span></label>
                                            <select id="dbAwsRegion" style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 8px; padding: 0.8rem; color: white; width: 100%;">
                                                <option value="us-east-1">US East (N. Virginia) - us-east-1</option>
                                                <option value="us-east-2">US East (Ohio) - us-east-2</option>
                                                <option value="us-west-1">US West (N. California) - us-west-1</option>
                                                <option value="us-west-2">US West (Oregon) - us-west-2</option>
                                                <option value="eu-west-1">EU (Ireland) - eu-west-1</option>
                                                <option value="eu-west-2">EU (London) - eu-west-2</option>
                                                <option value="eu-west-3">EU (Paris) - eu-west-3</option>
                                                <option value="eu-central-1">EU (Frankfurt) - eu-central-1</option>
                                                <option value="ap-southeast-1">Asia Pacific (Singapore) - ap-southeast-1</option>
                                                <option value="ap-southeast-2">Asia Pacific (Sydney) - ap-southeast-2</option>
                                                <option value="ap-south-1" selected>Asia Pacific (Mumbai) - ap-south-1</option>
                                                <option value="ap-northeast-1">Asia Pacific (Tokyo) - ap-northeast-1</option>
                                                <option value="ap-northeast-2">Asia Pacific (Seoul) - ap-northeast-2</option>
                                                <option value="ca-central-1">Canada (Central) - ca-central-1</option>
                                                <option value="sa-east-1">South America (São Paulo) - sa-east-1</option>
                                            </select>
                                        </div>
                                        <div class="input-group" style="margin-bottom: 1rem;">
                                            <label>Instance Type <span style="color: var(--anthropic-orange);">*</span></label>
                                            <select id="dbAwsInstanceType" style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 8px; padding: 0.8rem; color: white; width: 100%;">
                                                <option value="t2.micro" selected>t2.micro (1 vCPU, 1GB RAM) - Free tier eligible</option>
                                                <option value="t2.small">t2.small (1 vCPU, 2GB RAM)</option>
                                                <option value="t2.medium">t2.medium (2 vCPU, 4GB RAM)</option>
                                                <option value="t2.large">t2.large (2 vCPU, 8GB RAM)</option>
                                                <option value="t3.micro">t3.micro (2 vCPU, 1GB RAM) - Burstable</option>
                                                <option value="t3.small">t3.small (2 vCPU, 2GB RAM) - Burstable</option>
                                                <option value="t3.medium">t3.medium (2 vCPU, 4GB RAM) - Burstable</option>
                                                <option value="t3.large">t3.large (2 vCPU, 8GB RAM) - Burstable</option>
                                                <option value="m5.large">m5.large (2 vCPU, 8GB RAM) - General purpose</option>
                                                <option value="m5.xlarge">m5.xlarge (4 vCPU, 16GB RAM) - General purpose</option>
                                                <option value="c5.large">c5.large (2 vCPU, 4GB RAM) - Compute optimized</option>
                                                <option value="c5.xlarge">c5.xlarge (4 vCPU, 8GB RAM) - Compute optimized</option>
                                            </select>
                                        </div>
                                        <div class="input-group" style="margin-bottom: 1rem;">
                                            <label>Domain Name (Optional)</label>
                                            <input type="text" id="dbAwsDomain" placeholder="mcp.example.com" style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 8px; padding: 0.8rem; color: white; width: 100%;" />
                                            <small style="color: rgba(255, 255, 255, 0.6); font-size: 0.85rem; display: block; margin-top: 0.5rem;">Leave empty to use IP address. Format: subdomain.domain.com (no http:// or https://). Requires Route 53 hosted zone.</small>
                                        </div>
                                        <button onclick="deployDatabaseOnline('aws', '${configPath}', '${serverPath}', '${serverName}')" style="background: linear-gradient(135deg, #FF9900, #CC7A00); border: none; color: white; padding: 0.8rem 1.5rem; border-radius: 6px; cursor: pointer; font-weight: 600; width: 100%;">
                                            <i class="fas fa-cloud-upload-alt"></i> Deploy to AWS EC2
                                        </button>
                                    </div>

                                    <!-- Azure Tab Content -->
                                    <div id="azure-online-tab" class="online-tab-content" style="display: none;">
                                        <div class="input-group" style="margin-bottom: 1rem;">
                                            <label>Subscription ID <span style="color: var(--anthropic-orange);">*</span></label>
                                            <input type="text" id="dbAzureSubscriptionId" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 8px; padding: 0.8rem; color: white; width: 100%;" />
                                        </div>
                                        <div class="input-group" style="margin-bottom: 1rem;">
                                            <label>Client ID <span style="color: var(--anthropic-orange);">*</span></label>
                                            <input type="text" id="dbAzureClientId" placeholder="Application (client) ID" style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 8px; padding: 0.8rem; color: white; width: 100%;" />
                                        </div>
                                        <button onclick="deployDatabaseOnline('azure', '${configPath}', '${serverPath}', '${serverName}')" style="background: linear-gradient(135deg, #0078D4, #005A9E); border: none; color: white; padding: 0.8rem 1.5rem; border-radius: 6px; cursor: pointer; font-weight: 600; width: 100%;">
                                            <i class="fas fa-cloud-upload-alt"></i> Deploy to Azure VM
                                        </button>
                                    </div>

                                    <!-- Remote Tab Content -->
                                    <div id="remote-online-tab" class="online-tab-content" style="display: none;">
                                        <div class="input-group" style="margin-bottom: 1rem;">
                                            <label>Host/IP Address <span style="color: var(--anthropic-orange);">*</span></label>
                                            <input type="text" id="dbRemoteHost" placeholder="192.168.1.100 or server.example.com" style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 8px; padding: 0.8rem; color: white; width: 100%;" />
                                        </div>
                                        <div class="input-group" style="margin-bottom: 1rem;">
                                            <label>Username <span style="color: var(--anthropic-orange);">*</span></label>
                                            <input type="text" id="dbRemoteUsername" placeholder="ubuntu" value="ubuntu" style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 8px; padding: 0.8rem; color: white; width: 100%;" />
                                        </div>
                                        <div class="input-group" style="margin-bottom: 1rem;">
                                            <label>Password</label>
                                            <input type="password" id="dbRemotePassword" placeholder="Server password" style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 8px; padding: 0.8rem; color: white; width: 100%;" />
                                        </div>
                                        <button onclick="deployDatabaseOnline('remote', '${configPath}', '${serverPath}', '${serverName}')" style="background: linear-gradient(135deg, var(--scikiq-green), #059669); border: none; color: white; padding: 0.8rem 1.5rem; border-radius: 6px; cursor: pointer; font-weight: 600; width: 100%;">
                                            <i class="fas fa-cloud-upload-alt"></i> Deploy to Remote Server
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <!-- Manual Setup Instructions -->
                            <details style="background: rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 1rem; margin-bottom: 2rem;">
                                <summary style="cursor: pointer; font-weight: 600; color: var(--anthropic-orange); margin-bottom: 1rem;">
                                    <i class="fas fa-tools"></i> Manual Setup Instructions
                                </summary>

                            <!-- Step 2 -->
                            <div style="background: rgba(255, 255, 255, 0.05); border-left: 4px solid var(--anthropic-orange); padding: 1.5rem; margin-bottom: 1rem; border-radius: 8px;">
                                <div style="display: flex; align-items: start; gap: 1rem;">
                                    <div style="background: var(--anthropic-orange); width: 2rem; height: 2rem; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; flex-shrink: 0;">2</div>
                                    <div style="flex: 1;">
                                        <h4 style="margin: 0 0 0.5rem; color: var(--anthropic-orange);">Add to Claude Desktop Configuration</h4>
                                        <p style="margin: 0 0 1rem; color: rgba(255, 255, 255, 0.8);">
                                            Add this configuration to your Claude Desktop settings:
                                        </p>
                                        <div style="background: rgba(0, 0, 0, 0.6); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 8px; padding: 1rem; position: relative; font-family: 'Fira Code', monospace;">
<code style="color: rgba(255, 255, 255, 0.9);">{
  "mcpServers": {
    "${serverName}": {
      "command": "${pythonPath}",
      "args": [
        "${normalizedServerPath}\\run_mcp_server.py",
        "--config-file",
        "${normalizedConfigPath}"
      ]
    }
  }
}</code>
                                            <button onclick="copyDatabaseConfig('${configPath}', '${serverPath}', '${serverName}', '${pythonPath}')" style="position: absolute; top: 0.5rem; right: 0.5rem; background: rgba(255, 255, 255, 0.1); border: none; color: white; padding: 0.4rem 0.8rem; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">
                                                <i class="fas fa-copy"></i>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Step 3 -->
                            <div style="background: rgba(255, 255, 255, 0.05); border-left: 4px solid var(--anthropic-purple); padding: 1.5rem; margin-bottom: 1rem; border-radius: 8px;">
                                <div style="display: flex; align-items: start; gap: 1rem;">
                                    <div style="background: var(--anthropic-purple); width: 2rem; height: 2rem; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; flex-shrink: 0;">3</div>
                                    <div style="flex: 1;">
                                        <h4 style="margin: 0 0 0.5rem; color: var(--anthropic-purple);">Restart Claude Desktop</h4>
                                        <p style="margin: 0; color: rgba(255, 255, 255, 0.8);">
                                            Restart Claude Desktop application to load the new MCP server.
                                        </p>
                                    </div>
                                </div>
                            </div>

                            <!-- Step 4 -->
                            <div style="background: rgba(255, 255, 255, 0.05); border-left: 4px solid var(--success-green); padding: 1.5rem; margin-bottom: 2rem; border-radius: 8px;">
                                <div style="display: flex; align-items: start; gap: 1rem;">
                                    <div style="background: var(--success-green); width: 2rem; height: 2rem; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; flex-shrink: 0;">4</div>
                                    <div style="flex: 1;">
                                        <h4 style="margin: 0 0 0.5rem; color: var(--success-green);">Test Database Connection</h4>
                                        <p style="margin: 0; color: rgba(255, 255, 255, 0.8);">
                                            Ask Claude to list your databases or run a simple query to test the connection.
                                        </p>
                                    </div>
                                </div>
                            </div>

                                </div>
                            </details>

                            <!-- Configuration Summary -->
                            <div style="margin-top: 2rem; border-top: 2px solid rgba(255, 255, 255, 0.1); padding-top: 2rem;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                                    <h4 style="margin: 0; color: var(--scikiq-green);">
                                        <i class="fas fa-file-alt"></i> Generated Configuration
                                    </h4>
                                </div>
                                <div style="background: rgba(0, 0, 0, 0.6); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 8px; padding: 1.5rem; max-height: 300px; overflow-y: auto;">
                                    <pre style="margin: 0; color: rgba(255, 255, 255, 0.9); font-family: 'Fira Code', monospace; font-size: 0.9rem;" id="databaseConfigPreview">Loading configuration...</pre>
                                </div>
                                <div style="margin-top: 0.5rem; color: rgba(255, 255, 255, 0.6); font-size: 0.85rem;">
                                    <i class="fas fa-map-marker-alt"></i> Configuration saved to: ${configPath}
                                </div>
                            </div>

                            <!-- Action Buttons -->
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 2rem;">
                                <button onclick="window.open('${configPath}', '_blank')" style="padding: 1rem; background: linear-gradient(135deg, var(--scikiq-green), #059669); border: none; border-radius: 8px; color: white; font-weight: 600; cursor: pointer; font-size: 1rem;">
                                    <i class="fas fa-external-link-alt"></i> Open Config File
                                </button>
                                <button onclick="this.closest('[style*=fixed]').remove()" style="padding: 1rem; background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 8px; color: white; font-weight: 600; cursor: pointer; font-size: 1rem;">
                                    <i class="fas fa-check"></i> Done
                                </button>
                            </div>

                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHTML);

            // Load the actual configuration
            loadDatabaseConfig(configPath);
        }

        async function loadDatabaseConfig(configPath) {
            try {
                const response = await fetch(`/api/get-database-config?path=${encodeURIComponent(configPath)}`);
                const result = await response.json();

                if (result.success) {
                    const preview = document.getElementById('databaseConfigPreview');
                    if (preview) {
                        preview.textContent = result.config_content;
                    }
                }
            } catch (error) {
                console.error('Error loading database config:', error);
            }
        }

        function copyDatabaseConfig(configPath, serverPath, serverName, pythonPath) {
            // Ensure proper Windows path formatting
            const normalizedConfigPath = configPath.replace(/\//g, '\\');
            const normalizedServerPath = serverPath.replace(/\//g, '\\');

            const config = `{
  "mcpServers": {
    "${serverName}": {
      "command": "${pythonPath}",
      "args": [
        "${normalizedServerPath}\\run_mcp_server.py",
        "--config-file",
        "${normalizedConfigPath}"
      ]
    }
  }
}`;

            navigator.clipboard.writeText(config).then(() => {
                // Visual feedback
                const button = event.target;
                const originalContent = button.innerHTML;
                button.innerHTML = '<i class="fas fa-check"></i> Copied!';
                button.style.background = 'var(--success-green)';

                setTimeout(() => {
                    button.innerHTML = originalContent;
                    button.style.background = 'rgba(255, 255, 255, 0.1)';
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy: ', err);
                alert('Failed to copy to clipboard. Please copy manually.');
            });
        }

        async function autoDeployDatabaseMCP(configPath, serverPath, serverName) {
            try {
                const button = event.target;
                const originalText = button.innerHTML;
                button.innerHTML = '<div class="loading-spinner"></div> Deploying...';
                button.disabled = true;

                const response = await fetch('/api/auto-deploy-database-mcp', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        config_path: configPath,
                        server_path: serverPath,
                        server_name: serverName
                    })
                });

                const result = await response.json();

                if (result.success) {
                    button.innerHTML = '<i class="fas fa-check"></i> Deployed Successfully!';
                    button.style.background = 'var(--success-green)';

                    // Show success message
                    setTimeout(() => {
                        alert('Database MCP server deployed successfully! Please restart Claude Desktop to use the new server.');
                    }, 500);
                } else {
                    throw new Error(result.error || 'Deployment failed');
                }

            } catch (error) {
                console.error('Auto-deployment error:', error);
                alert('Auto-deployment failed: ' + error.message + '. Please use manual setup instructions.');

                const button = event.target;
                button.innerHTML = originalText;
                button.disabled = false;
            }
        }

        function renderSwaggerEndpointsTree(apis, swaggerUrl) {
            const fileTree = document.getElementById('fileTree');
            fileTree.innerHTML = '';

            // Create header for Swagger source
            const header = document.createElement('div');
            header.className = 'file-tree-item directory';
            header.style.borderBottom = '1px solid rgba(255, 255, 255, 0.1)';
            header.style.marginBottom = '0.5rem';
            header.innerHTML = `
                <span class="icon"><i class="fas fa-file-code" style="color: #10B981;"></i></span>
                <span style="flex: 1; font-weight: 700;">Swagger API</span>
                <span style="font-size: 0.65rem; color: rgba(255,255,255,0.4); margin-left: 0.5rem;">${apis.length} endpoints</span>
            `;
            header.title = swaggerUrl;
            fileTree.appendChild(header);

            // Group endpoints by path segments (creates a tree structure)
            const pathGroups = {};
            apis.forEach((api, index) => {
                const route = api.route;
                const pathParts = route.split('/').filter(p => p);

                // Use first segment as the group (or 'root' if no segments)
                const groupName = pathParts.length > 0 ? '/' + pathParts[0] : '/';

                if (!pathGroups[groupName]) {
                    pathGroups[groupName] = [];
                }
                pathGroups[groupName].push({ ...api, index });
            });

            // Sort groups alphabetically
            const sortedGroups = Object.keys(pathGroups).sort();

            // Render each group
            sortedGroups.forEach(groupName => {
                const endpoints = pathGroups[groupName];

                // Create group container
                const groupDiv = document.createElement('div');
                groupDiv.style.marginBottom = '0.3rem';

                // Group header
                const groupHeader = document.createElement('div');
                groupHeader.className = 'file-tree-item directory';
                groupHeader.style.fontWeight = '600';
                groupHeader.innerHTML = `
                    <span class="icon"><i class="fas fa-folder" style="color: #F59E0B;"></i></span>
                    <span style="flex: 1;">${groupName}</span>
                    <span style="font-size: 0.65rem; color: rgba(255,255,255,0.4); margin-left: 0.5rem;">${endpoints.length}</span>
                `;
                groupDiv.appendChild(groupHeader);

                // Create children container for endpoints
                const childContainer = document.createElement('div');
                childContainer.className = 'file-tree-children';
                childContainer.style.display = 'block'; // Always expanded

                endpoints.forEach(api => {
                    const item = document.createElement('div');
                    item.className = 'file-tree-item';
                    item.setAttribute('data-route', api.route);

                    // Method color coding
                    const methodColors = {
                        'GET': '#10B981',
                        'POST': '#3B82F6',
                        'PUT': '#F59E0B',
                        'DELETE': '#EF4444',
                        'PATCH': '#8B5CF6'
                    };

                    const method = api.methods[0];
                    const methodColor = methodColors[method] || '#9CA3AF';

                    item.innerHTML = `
                        <span class="icon"><i class="fas fa-plug" style="color: ${methodColor};"></i></span>
                        <span style="flex: 1;">${escapeHtml(api.route)}</span>
                        <span style="background: ${methodColor}; color: white; padding: 0.1rem 0.4rem; border-radius: 4px; font-size: 0.65rem; margin-left: 0.5rem;">${method}</span>
                    `;

                    item.title = `${method} ${api.route}\n${api.docstring || 'No description'}`;
                    item.style.cursor = 'pointer';

                    // Highlight corresponding API in center panel on click
                    item.onclick = () => {
                        // Remove previous selection
                        document.querySelectorAll('.file-tree-item').forEach(el => el.classList.remove('selected'));
                        item.classList.add('selected');

                        // Scroll to and highlight the API card in center panel
                        const apiCards = document.querySelectorAll('.api-card');
                        if (apiCards[api.index]) {
                            apiCards[api.index].scrollIntoView({ behavior: 'smooth', block: 'center' });

                            // Add temporary highlight effect
                            apiCards[api.index].style.transition = 'all 0.3s ease';
                            apiCards[api.index].style.boxShadow = '0 0 20px rgba(255, 111, 0, 0.5)';
                            setTimeout(() => {
                                apiCards[api.index].style.boxShadow = '';
                            }, 1500);
                        }
                    };

                    childContainer.appendChild(item);
                });

                groupDiv.appendChild(childContainer);
                fileTree.appendChild(groupDiv);
            });
        }

        function renderCodebaseEndpointsTree(apis, intelligence) {
            const fileTree = document.getElementById('fileTree');
            fileTree.innerHTML = '';

            // Create header for codebase source
            const projectType = intelligence?.project_type || 'Python API';
            const frameworks = intelligence?.frameworks?.join(', ') || 'Unknown';

            const header = document.createElement('div');
            header.className = 'file-tree-item directory';
            header.style.borderBottom = '1px solid rgba(255, 255, 255, 0.1)';
            header.style.marginBottom = '0.5rem';
            header.innerHTML = `
                <span class="icon"><i class="fas fa-code-branch" style="color: #10B981;"></i></span>
                <span style="flex: 1; font-weight: 700;">${projectType}</span>
                <span style="font-size: 0.65rem; color: rgba(255,255,255,0.4); margin-left: 0.5rem;">${apis.length} endpoints</span>
            `;
            header.title = `Framework: ${frameworks}\nEndpoints: ${apis.length}`;
            fileTree.appendChild(header);

            // Group endpoints by business domain (like Swagger tags)
            const domainGroups = {};
            apis.forEach((api, index) => {
                const domain = api.business_domain || 'general';

                if (!domainGroups[domain]) {
                    domainGroups[domain] = [];
                }
                domainGroups[domain].push({ ...api, index });
            });

            // Sort domains alphabetically
            const sortedDomains = Object.keys(domainGroups).sort();

            // Render each domain group
            sortedDomains.forEach(domain => {
                const endpoints = domainGroups[domain];

                // Create group container
                const groupDiv = document.createElement('div');
                groupDiv.style.marginBottom = '0.3rem';

                // Domain icon mapping
                const domainIcons = {
                    'insurance': 'fa-shield-alt',
                    'health': 'fa-heartbeat',
                    'financial': 'fa-dollar-sign',
                    'customer': 'fa-users',
                    'product': 'fa-box',
                    'administration': 'fa-cog',
                    'general': 'fa-folder'
                };
                const domainIcon = domainIcons[domain] || 'fa-folder';

                // Group header
                const groupHeader = document.createElement('div');
                groupHeader.className = 'file-tree-item directory';
                groupHeader.style.fontWeight = '600';
                groupHeader.innerHTML = `
                    <span class="icon"><i class="fas ${domainIcon}" style="color: #F59E0B;"></i></span>
                    <span style="flex: 1;">${domain.charAt(0).toUpperCase() + domain.slice(1)}</span>
                    <span style="font-size: 0.65rem; color: rgba(255,255,255,0.4); margin-left: 0.5rem;">${endpoints.length}</span>
                `;
                groupDiv.appendChild(groupHeader);

                // Create children container for endpoints
                const childContainer = document.createElement('div');
                childContainer.className = 'file-tree-children';
                childContainer.style.display = 'block'; // Always expanded

                endpoints.forEach(api => {
                    const item = document.createElement('div');
                    item.className = 'file-tree-item';
                    item.setAttribute('data-route', api.route);
                    item.setAttribute('data-file', api.file);

                    // Method color coding
                    const methodColors = {
                        'GET': '#10B981',
                        'POST': '#3B82F6',
                        'PUT': '#F59E0B',
                        'DELETE': '#EF4444',
                        'PATCH': '#8B5CF6'
                    };

                    const method = api.methods[0];
                    const methodColor = methodColors[method] || '#9CA3AF';

                    // Show file name as badge
                    const fileName = api.file_name || '';
                    const fileBadge = fileName ? `<span style="background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.6); padding: 0.1rem 0.4rem; border-radius: 4px; font-size: 0.6rem; margin-left: 0.3rem; font-family: 'Fira Code', monospace;">${fileName}</span>` : '';

                    item.innerHTML = `
                        <span class="icon"><i class="fas fa-plug" style="color: ${methodColor};"></i></span>
                        <span style="flex: 1;">${escapeHtml(api.route)}</span>
                        <span style="background: ${methodColor}; color: white; padding: 0.1rem 0.4rem; border-radius: 4px; font-size: 0.65rem; margin-left: 0.5rem;">${method}</span>
                        ${fileBadge}
                    `;

                    const confidence = Math.round(api.confidence * 100);
                    item.title = `${method} ${api.route}\nFunction: ${api.function_name}\nFile: ${fileName} (line ${api.line_number})\nConfidence: ${confidence}%\n\n${api.docstring || 'No description'}`;
                    item.style.cursor = 'pointer';

                    // Highlight corresponding API in center panel on click
                    item.onclick = () => {
                        // Remove previous selection
                        document.querySelectorAll('.file-tree-item').forEach(el => el.classList.remove('selected'));
                        item.classList.add('selected');

                        // Scroll to and highlight the API card in center panel
                        const apiCards = document.querySelectorAll('.api-card');
                        if (apiCards[api.index]) {
                            apiCards[api.index].scrollIntoView({ behavior: 'smooth', block: 'center' });

                            // Add temporary highlight effect
                            apiCards[api.index].style.transition = 'all 0.3s ease';
                            apiCards[api.index].style.boxShadow = '0 0 20px rgba(0, 163, 224, 0.5)';
                            setTimeout(() => {
                                apiCards[api.index].style.boxShadow = '';
                            }, 1500);
                        }
                    };

                    childContainer.appendChild(item);
                });

                groupDiv.appendChild(childContainer);
                fileTree.appendChild(groupDiv);
            });
        }

        async function importFromSwagger() {
            const swaggerUrl = document.getElementById('swaggerUrl').value;
            const apiBaseUrl = document.getElementById('baseUrl').value;
            const authType = document.getElementById('authType').value;
            const authToken = document.getElementById('authToken').value;
            const authUser = document.getElementById('authUser').value;
            const authPass = document.getElementById('authPass').value;
            const verifySsl = document.getElementById('verifySsl').checked;
            const timeout = parseInt(document.getElementById('requestTimeout').value);
            const apiName = document.getElementById('apiName').value;

            // OAuth configuration
            const enableOAuth = document.getElementById('enableOAuthSwagger').checked;

            if (!swaggerUrl) {
                alert('Please enter a Swagger URL');
                return;
            }

            // Hide Code Viewer tab for Swagger MCP server
            const codeViewerTab = document.getElementById('code-viewer-tab');
            if (codeViewerTab) {
                codeViewerTab.style.display = 'none';
            }

            // Store the Swagger configuration
            projectSourceType = 'swagger';
            selectedSwaggerConfig = {
                swagger_url: swaggerUrl,
                api_base_url: apiBaseUrl,
                auth_type: authType,
                auth_token: authToken,
                enable_oauth: enableOAuth,
                auth_user: authUser,
                auth_pass: authPass,
                verify_ssl: verifySsl,
                timeout: timeout,
                api_name: apiName
            };

            closeSwaggerModal();
            hideWelcomeScreen();

            // Show loading state
            document.getElementById('scanBtn').disabled = true;
            document.getElementById('scanBtn').innerHTML = '<div class="spinner"></div> Parsing Swagger...';

            try {
                const response = await fetch('/api/parse-swagger', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        swagger_url: swaggerUrl,
                        api_base_url: apiBaseUrl
                    })
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                projectData = await response.json();

                // Update UI with parsed APIs
                if (projectData.api_definitions) {
                    renderAPIs(projectData.api_definitions);

                    // Render API endpoints as a tree in left pane
                    renderSwaggerEndpointsTree(projectData.api_definitions, swaggerUrl);

                    // Update stats (simplified for Swagger - no file tree)
                    document.getElementById('totalFiles').textContent = '0';
                    document.getElementById('apisFound').textContent = projectData.api_definitions.length;

                    // Enable action buttons
                    document.getElementById('bulkAnalyzeBtn').disabled = false;
                    document.getElementById('docsBtn').disabled = false;

                    // Update bulk analyze button text with count
                    updateBulkAnalyzeButton();

                    // Show success message
                    document.getElementById('scanBtn').innerHTML = '<i class="fas fa-check"></i> Swagger Parsed Successfully';
                    setTimeout(() => {
                        document.getElementById('scanBtn').innerHTML = '<i class="fas fa-sync-alt"></i> Re-import Swagger';
                        document.getElementById('scanBtn').disabled = false;
                    }, 3000);
                } else {
                    throw new Error('No API definitions found in response');
                }

            } catch (error) {
                console.error('Swagger import error:', error);
                alert(`Failed to import Swagger spec: ${error.message}\n\nPlease check the URL and try again.`);
                document.getElementById('scanBtn').innerHTML = '<i class="fas fa-sync-alt"></i> Re-import Swagger';
                document.getElementById('scanBtn').disabled = false;
            }
        }

        // Store selected project configuration and source type
        let projectSourceType = 'folder'; // 'folder' or 'swagger'
        let selectedProjectConfig = {
            project_path: '',  // Will be populated from config
            source_file: ''     // Will be populated from config
        };
        let selectedSwaggerConfig = {
            swagger_url: '',
            api_base_url: ''
        };

        async function scanFromCodebase() {
            const codebaseSourceType = document.getElementById('codebaseSourceType').value;
            
            let projectPath, sourceFile, apiBaseUrl;
            let githubRepoUrl, githubBranch, githubToken;

            if (codebaseSourceType === 'github') {
                githubRepoUrl = document.getElementById('githubRepoUrl').value;
                githubBranch = document.getElementById('githubBranch').value || 'main';
                githubToken = document.getElementById('githubToken').value;
                sourceFile = document.getElementById('sourceFile').value;
                apiBaseUrl = document.getElementById('apiServerUrl').value;

                if (!githubRepoUrl) {
                    alert('Please enter a GitHub repository URL');
                    return;
                }
            } else {
                projectPath = document.getElementById('projectPath').value;
                sourceFile = document.getElementById('sourceFile').value;
                apiBaseUrl = document.getElementById('apiServerUrl').value;

                if (!projectPath) {
                    alert('Please enter a project path');
                    return;
                }
            }

            // OAuth configuration
            const enableOAuth = document.getElementById('enableOAuthCodebase').checked;

            // Store the configuration (similar to Swagger config)
            projectSourceType = codebaseSourceType === 'github' ? 'github' : 'folder';
            
            // Show and activate Code Viewer tab for codebase MCP server
            const codeViewerTab = document.getElementById('code-viewer-tab');
            if (codeViewerTab) {
                codeViewerTab.style.display = 'flex';
                // Also make it active and switch to code tab
                document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
                codeViewerTab.classList.add('active');
                document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
                document.getElementById('code-tab').classList.add('active');
            }
            
            selectedProjectConfig = {
                source_type: codebaseSourceType,
                project_path: projectPath,
                github_repo_url: githubRepoUrl,
                github_branch: githubBranch,
                github_token: githubToken,
                source_file: sourceFile,
                api_base_url: apiBaseUrl || 'http://localhost:5000',
                enable_oauth: enableOAuth
            };

            closeCodebaseModal();
            hideWelcomeScreen();
            scanProject();
        }

        function hideWelcomeScreen() {
            document.getElementById('welcomeScreen').style.display = 'none';
            document.getElementById('mainContainer').style.display = 'grid';
        }

        // Wrapper function to handle re-scanning based on source type
        async function rescanSource() {
            if (projectSourceType === 'swagger') {
                // Re-import from Swagger
                await importFromSwaggerDirect();
            } else {
                // Re-scan from folder
                await scanProject();
            }
        }

        // Direct import without showing modal (for re-scan)
        async function importFromSwaggerDirect() {
            const btn = document.getElementById('scanBtn');
            btn.disabled = true;
            btn.innerHTML = '<div class="spinner"></div> Re-parsing Swagger...';

            try {
                const response = await fetch('/api/parse-swagger', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(selectedSwaggerConfig)
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                projectData = await response.json();

                // Update UI with parsed APIs
                if (projectData.api_definitions) {
                    renderAPIs(projectData.api_definitions);
                    renderSwaggerEndpointsTree(projectData.api_definitions, selectedSwaggerConfig.swagger_url);

                    // Update stats
                    document.getElementById('totalFiles').textContent = '0';
                    document.getElementById('apisFound').textContent = projectData.api_definitions.length;

                    // Enable action buttons
                    document.getElementById('bulkAnalyzeBtn').disabled = false;
                    document.getElementById('docsBtn').disabled = false;

                    // Update bulk analyze button text with count
                    updateBulkAnalyzeButton();

                    btn.innerHTML = '<i class="fas fa-check"></i> Swagger Re-parsed Successfully';
                    setTimeout(() => {
                        btn.innerHTML = '<i class="fas fa-sync-alt"></i> Re-import Swagger';
                        btn.disabled = false;
                    }, 3000);
                } else {
                    throw new Error('No API definitions found in response');
                }

            } catch (error) {
                console.error('Swagger re-import error:', error);
                alert(`Failed to re-import Swagger spec: ${error.message}`);
                btn.innerHTML = '<i class="fas fa-sync-alt"></i> Re-import Swagger';
                btn.disabled = false;
            }
        }

        async function scanProject() {
            const btn = document.getElementById('scanBtn');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<div class="spinner"></div> Scanning Codebase...';
            }

            try {
                const response = await fetch('/api/scan-project', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(selectedProjectConfig)
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                projectData = await response.json();

                // Display URLs in tree format (like Swagger), not file tree
                if (projectData.api_definitions) {
                    renderAPIs(projectData.api_definitions);

                    // Render URL tree grouped by business domain (like Swagger tags)
                    renderCodebaseEndpointsTree(projectData.api_definitions, projectData.intelligence);
                }

                // Update stats
                document.getElementById('totalFiles').textContent = '0'; // Not showing files anymore
                document.getElementById('apisFound').textContent = projectData.total_apis || projectData.api_definitions.length;

                // Enable buttons
                document.getElementById('docsBtn').disabled = false;
                document.getElementById('bulkAnalyzeBtn').disabled = false;

                // Update bulk analyze button text with count
                updateBulkAnalyzeButton();

                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-check"></i> Scan Complete';

                setTimeout(() => {
                    btn.innerHTML = '<i class="fas fa-sync-alt"></i> Re-scan Project';
                }, 2000);

            } catch (error) {
                console.error('Scan error:', error);
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Scan Failed';
                alert(`Failed to scan project: ${error.message}`);
            }
        }

        function renderFileTree(tree, container = null) {
            if (!container) {
                container = document.getElementById('fileTree');
                container.innerHTML = '';
            }

            const item = document.createElement('div');
            item.className = 'file-tree-item' + (tree.type === 'directory' ? ' directory' : '');
            item.setAttribute('data-path', tree.path);

            const icon = tree.type === 'directory' ? 'fa-folder' : 'fa-file-code';

            // Color code and label by file type
            let iconColor = '';
            let fileLabel = '';

            if (tree.extension === '.py') {
                iconColor = 'color: #3776AB;';
                fileLabel = 'Python';
                if (tree.name.includes('route') || tree.name.includes('api')) {
                    fileLabel = 'API Route';
                }
            } else if (tree.extension === '.json') {
                iconColor = 'color: #00A859;';
                fileLabel = 'JSON';
            } else if (tree.extension === '.yaml' || tree.extension === '.yml') {
                iconColor = 'color: #F59E0B;';
                fileLabel = 'YAML';
            } else if (tree.extension === '.txt') {
                iconColor = 'color: #9CA3AF;';
                fileLabel = 'Text';
            } else if (tree.extension === '.env') {
                iconColor = 'color: #10B981;';
                fileLabel = 'ENV';
            }

            // Add badge for important API files
            let badge = '';
            if (tree.name.includes('route') || tree.name.includes('api')) {
                badge = '<span style="background: var(--anthropic-orange); color: white; padding: 0.1rem 0.4rem; border-radius: 4px; font-size: 0.65rem; margin-left: 0.5rem;">API</span>';
            } else if (tree.name === 'app.py' || tree.name === 'main.py') {
                badge = '<span style="background: var(--success-green); color: white; padding: 0.1rem 0.4rem; border-radius: 4px; font-size: 0.65rem; margin-left: 0.5rem;">MAIN</span>';
            }

            item.innerHTML = `
                <span class="icon"><i class="fas ${icon}" style="${iconColor}"></i></span>
                <span style="flex: 1;">${tree.name}</span>
                ${badge}
                ${tree.type === 'file' && fileLabel ? `<span style="font-size: 0.65rem; color: rgba(255,255,255,0.4); margin-left: 0.5rem;">${fileLabel}</span>` : ''}
            `;

            // Add tooltip
            if (tree.type === 'file') {
                item.title = `${tree.name}\nType: ${fileLabel}\nSize: ${(tree.size / 1024).toFixed(1)} KB\nClick to view`;
            }

            if (tree.type === 'file' && tree.scannable) {
                item.onclick = () => {
                    // Remove previous selection
                    document.querySelectorAll('.file-tree-item').forEach(el => el.classList.remove('selected'));

                    // Add selection to clicked item
                    item.classList.add('selected');

                    // Load file
                    loadFile(tree.path, tree.name);
                };
                item.style.cursor = 'pointer';
            }

            container.appendChild(item);

            if (tree.children && tree.children.length > 0) {
                const childContainer = document.createElement('div');
                childContainer.className = 'file-tree-children';

                for (const child of tree.children) {
                    renderFileTree(child, childContainer);
                }

                container.appendChild(childContainer);
            }
        }

        async function loadFile(path, name) {
            document.getElementById('currentFile').textContent = name;

            try {
                const response = await fetch('/api/read-file', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ file_path: path })
                });

                const data = await response.json();

                if (data.success) {
                    document.getElementById('codeContent').textContent = data.content;
                }
            } catch (error) {
                console.error('File load error:', error);
            }
        }

        // Store all APIs globally for selection
        window.allAPIs = [];
        window.selectedAPIs = new Set();

        function renderAPIs(apis) {
            const container = document.getElementById('apisList');
            container.innerHTML = '';

            // Store APIs globally
            window.allAPIs = apis;

            // Group APIs by business domain
            const domainGroups = {};
            apis.forEach((api, index) => {
                api.index = index; // Add index for selection tracking
                const domain = api.business_domain || 'General';
                if (!domainGroups[domain]) {
                    domainGroups[domain] = {
                        apis: [],
                        highConfidence: 0,
                        total: 0
                    };
                }
                domainGroups[domain].apis.push(api);
                domainGroups[domain].total++;
                // Count high MCP suitability (≥80%) - only if AI has analyzed it
                if (api.mcp_suitability_score && api.mcp_suitability_score >= 80) {
                    domainGroups[domain].highConfidence++;
                }
            });

            // Domain icons mapping
            const domainIcons = {
                'Administration': 'fa-user-shield',
                'Customer': 'fa-users',
                'Financial': 'fa-chart-line',
                'General': 'fa-globe',
                'Health': 'fa-heartbeat',
                'Insurance': 'fa-shield-alt',
                'Product': 'fa-box',
                'Network': 'fa-network-wired',
                'Claims': 'fa-file-medical',
                'Quote': 'fa-file-invoice-dollar'
            };

            // Render each domain group
            Object.keys(domainGroups).sort().forEach(domain => {
                const group = domainGroups[domain];
                const icon = domainIcons[domain] || 'fa-folder';

                const domainDiv = document.createElement('div');
                domainDiv.className = 'domain-group domain-expanded';
                domainDiv.innerHTML = `
                    <div class="domain-header" onclick="toggleDomain(this)">
                        <input type="checkbox" class="domain-checkbox" onclick="event.stopPropagation(); toggleDomainSelection(this, '${domain}')" />
                        <i class="fas ${icon} domain-icon" style="color: var(--scikiq-light-blue);"></i>
                        <span class="domain-name">${domain}</span>
                        <div class="domain-badge">
                            <span class="high">${group.highConfidence}</span>
                            <span>/</span>
                            <span class="total">${group.total}</span>
                        </div>
                        <i class="fas fa-chevron-right domain-expand"></i>
                    </div>
                    <div class="domain-apis">
                        ${group.apis.map(api => renderAPIItem(api, domain)).join('')}
                    </div>
                `;

                container.appendChild(domainDiv);
            });

            updateSelectionCount();
        }

        function renderAPIItem(api, domain) {
            const method = api.methods[0] || 'GET';

            // Use MCP suitability score if available, otherwise show as pending
            const mcpScore = api.mcp_suitability_score;
            let scoreDisplay = '';
            let confidenceClass = 'confidence-pending';

            if (mcpScore !== undefined && mcpScore !== null) {
                scoreDisplay = `${Math.round(mcpScore)}%`;
                if (mcpScore >= 80) confidenceClass = 'confidence-high';
                else if (mcpScore >= 60) confidenceClass = 'confidence-medium';
                else confidenceClass = 'confidence-low';
            } else {
                scoreDisplay = '—';
                confidenceClass = 'confidence-pending';
            }

            return `
                <div class="api-item" data-api-index="${api.index}" data-domain="${domain}">
                    <input type="checkbox" class="api-checkbox" onchange="toggleAPISelection(${api.index})" />
                    <span class="api-method method-${method}">${method}</span>
                    <span class="api-route">${escapeHtml(api.route)}</span>
                    <span class="api-confidence ${confidenceClass}" title="MCP Suitability Score (AI-analyzed)">${scoreDisplay}</span>
                </div>
            `;
        }

        function toggleDomain(header) {
            const domainGroup = header.parentElement;
            domainGroup.classList.toggle('domain-expanded');
        }

        function toggleDomainSelection(checkbox, domain) {
            const apis = window.allAPIs.filter(api => (api.business_domain || 'General') === domain);
            apis.forEach(api => {
                if (checkbox.checked) {
                    window.selectedAPIs.add(api.index);
                } else {
                    window.selectedAPIs.delete(api.index);
                }
                // Update checkbox visual
                const apiCheckbox = document.querySelector(`.api-checkbox[onchange*="${api.index}"]`);
                if (apiCheckbox) apiCheckbox.checked = checkbox.checked;
            });
            updateSelectionCount();
        }

        function toggleAPISelection(apiIndex) {
            if (window.selectedAPIs.has(apiIndex)) {
                window.selectedAPIs.delete(apiIndex);
            } else {
                window.selectedAPIs.add(apiIndex);
            }
            updateSelectionCount();

            // Update domain checkbox if needed
            const apiItem = document.querySelector(`.api-item[data-api-index="${apiIndex}"]`);
            const domain = apiItem.dataset.domain;
            updateDomainCheckbox(domain);
        }

        function updateDomainCheckbox(domain) {
            const domainAPIs = window.allAPIs.filter(api => (api.business_domain || 'General') === domain);
            const selectedInDomain = domainAPIs.filter(api => window.selectedAPIs.has(api.index)).length;
            const domainCheckbox = document.querySelector(`.domain-header input[onclick*="${domain}"]`);

            if (domainCheckbox) {
                domainCheckbox.checked = selectedInDomain === domainAPIs.length && domainAPIs.length > 0;
                domainCheckbox.indeterminate = selectedInDomain > 0 && selectedInDomain < domainAPIs.length;
            }
        }

        function updateSelectionCount() {
            document.getElementById('selectedCount').textContent = window.selectedAPIs.size;
            document.getElementById('analyzeSelectedBtn').disabled = window.selectedAPIs.size === 0;
            document.getElementById('convertSelectedBtn').disabled = window.selectedAPIs.size === 0;
        }

        function selectAllAPIs() {
            window.allAPIs.forEach(api => window.selectedAPIs.add(api.index));
            document.querySelectorAll('.api-checkbox, .domain-checkbox').forEach(cb => cb.checked = true);
            updateSelectionCount();
        }

        function selectNoneAPIs() {
            window.selectedAPIs.clear();
            document.querySelectorAll('.api-checkbox, .domain-checkbox').forEach(cb => {
                cb.checked = false;
                cb.indeterminate = false;
            });
            updateSelectionCount();
        }

        function selectHighConfidenceAPIs() {
            selectNoneAPIs();
            window.allAPIs.forEach(api => {
                const confidence = api.confidence || 0.85;
                if (confidence >= 0.8) {
                    window.selectedAPIs.add(api.index);
                    const checkbox = document.querySelector(`.api-checkbox[onchange*="${api.index}"]`);
                    if (checkbox) checkbox.checked = true;
                }
            });
            // Update domain checkboxes
            const domains = [...new Set(window.allAPIs.map(api => api.business_domain || 'General'))];
            domains.forEach(domain => updateDomainCheckbox(domain));
            updateSelectionCount();
        }

        // Score range filter functions
        function updateAPIRangeFilter() {
            const minSlider = document.getElementById('apiMinScoreSlider');
            const maxSlider = document.getElementById('apiMaxScoreSlider');
            const minDisplay = document.getElementById('apiMinScoreDisplay');
            const maxDisplay = document.getElementById('apiMaxScoreDisplay');
            const rangeTrack = document.getElementById('rangeTrack');

            let minVal = parseInt(minSlider.value);
            let maxVal = parseInt(maxSlider.value);

            // Prevent min from exceeding max
            if (minVal > maxVal) {
                if (this === minSlider) {
                    minSlider.value = maxVal;
                    minVal = maxVal;
                } else {
                    maxSlider.value = minVal;
                    maxVal = minVal;
                }
            }

            // Update displays
            minDisplay.textContent = minVal + '%';
            maxDisplay.textContent = maxVal + '%';

            // Update display colors based on values
            function getColor(val) {
                if (val < 25) return '#EF4444';
                else if (val < 50) return '#F59E0B';
                else if (val < 75) return '#10B981';
                else return '#059669';
            }
            minDisplay.style.background = getColor(minVal);
            maxDisplay.style.background = getColor(maxVal);

            // Update range track position
            const minPercent = minVal;
            const maxPercent = maxVal;
            rangeTrack.style.left = minPercent + '%';
            rangeTrack.style.width = (maxPercent - minPercent) + '%';

            // Filter APIs by range
            filterAPIsByScoreRange(minVal / 100, maxVal / 100);
        }

        function resetAPIScoreFilter() {
            const minSlider = document.getElementById('apiMinScoreSlider');
            const maxSlider = document.getElementById('apiMaxScoreSlider');
            minSlider.value = 0;
            maxSlider.value = 100;
            updateAPIRangeFilter();
        }

        function filterAPIsByScoreRange(minScore, maxScore) {
            if (!window.allAPIs) return;

            // Hide APIs outside the score range
            window.allAPIs.forEach(api => {
                const score = api.mcp_suitability_score || (api.confidence * 100) || 85;
                const apiRow = document.querySelector(`[data-api-index="${api.index}"]`);

                if (apiRow) {
                    const scorePercent = score;
                    if (scorePercent >= (minScore * 100) && scorePercent <= (maxScore * 100)) {
                        apiRow.style.display = '';
                    } else {
                        apiRow.style.display = 'none';
                        // Uncheck if hidden
                        const checkbox = apiRow.querySelector('.api-checkbox');
                        if (checkbox && checkbox.checked) {
                            checkbox.checked = false;
                            window.selectedAPIs.delete(api.index);
                        }
                    }
                }
            });

            updateSelectionCount();

            // Show count of visible APIs
            const visibleCount = window.allAPIs.filter(api => {
                const score = api.mcp_suitability_score || (api.confidence * 100) || 85;
                return score >= (minScore * 100) && score <= (maxScore * 100);
            }).length;

            console.log(`Showing ${visibleCount} of ${window.allAPIs.length} APIs (score range: ${(minScore * 100).toFixed(0)}% - ${(maxScore * 100).toFixed(0)}%)`);
        }

        // Initialize range track on page load
        document.addEventListener('DOMContentLoaded', function() {
            const rangeTrack = document.getElementById('rangeTrack');
            if (rangeTrack) {
                rangeTrack.style.left = '0%';
                rangeTrack.style.width = '100%';
            }
        });

        async function analyzeSelectedAPIs() {
            if (window.selectedAPIs.size === 0) return;

            const selectedEndpoints = Array.from(window.selectedAPIs).map(index => window.allAPIs[index]);

            const btn = document.getElementById('analyzeSelectedBtn');
            btn.disabled = true;
            btn.innerHTML = '<div class="spinner"></div> Analyzing...';

            try {
                const response = await fetch('/api/bulk-analyze-apis', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        endpoints: selectedEndpoints,
                        min_confidence: 0 // Get all results
                    })
                });

                const result = await response.json();

                if (result.success) {
                    // Update projectData with MCP scores for analyzed APIs
                    if (result.all_analyzed_apis) {
                        result.all_analyzed_apis.forEach((analyzedApi) => {
                            // Find matching API in projectData by route
                            const matchingIndex = projectData.api_definitions.findIndex(
                                api => api.route === analyzedApi.route && api.methods[0] === analyzedApi.methods[0]
                            );
                            if (matchingIndex !== -1) {
                                projectData.api_definitions[matchingIndex].mcp_suitability_score = analyzedApi.analysis.mcp_score;
                                projectData.api_definitions[matchingIndex].analysis = analyzedApi.analysis;
                            }
                        });

                        // Re-render APIs with updated scores
                        renderAPIs(projectData.api_definitions);
                    }

                    // Store high confidence APIs FIRST before showing modal
                    window.highConfidenceAPIs = result.high_confidence_apis;

                    // Show summary modal
                    showBulkAnalysisSummary(result);
                    btn.innerHTML = '<i class="fas fa-check"></i> Analyzed!';
                } else {
                    throw new Error(result.error);
                }
            } catch (error) {
                alert('Analysis failed: ' + error.message);
                btn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Failed';
            } finally {
                setTimeout(() => {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fas fa-microscope"></i> Analyze Selected';
                }, 2000);
            }
        }

        async function convertSelectedAPIs() {
            if (window.selectedAPIs.size === 0) return;

            const selectedEndpoints = Array.from(window.selectedAPIs).map(index => window.allAPIs[index]);

            const btn = document.getElementById('convertSelectedBtn');
            btn.disabled = true;
            btn.innerHTML = '<div class="spinner"></div> Converting...';

            try {
                // Get base URL from either Swagger config or folder scan config
                let baseUrl = '';
                if (projectSourceType === 'swagger' && selectedSwaggerConfig.api_base_url) {
                    baseUrl = selectedSwaggerConfig.api_base_url;
                } else if (selectedProjectConfig.api_base_url) {
                    baseUrl = selectedProjectConfig.api_base_url;
                } else {
                    // Fallback: try to read from input field
                    const baseUrlInput = document.getElementById('baseUrl');
                    const apiServerUrlInput = document.getElementById('apiServerUrl');
                    if (baseUrlInput && baseUrlInput.value) {
                        baseUrl = baseUrlInput.value;
                    } else if (apiServerUrlInput && apiServerUrlInput.value) {
                        baseUrl = apiServerUrlInput.value;
                    }
                }

                // Get server name from input field if available
                const serverNameInput = document.getElementById('apiName');
                const serverName = serverNameInput ? serverNameInput.value : 'scikiq-mcp-autoAPI';

                const response = await fetch('/api/batch-convert-to-mcp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        endpoints: selectedEndpoints,
                        output_file: 'mcp_server_selected.py',
                        base_url: baseUrl,
                        server_name: serverName
                    })
                });

                const result = await response.json();

                if (result.success) {
                    // Store yaml_path and output_path for later use
                    if (result.yaml_path) {
                        window.lastGeneratedYamlPath = result.yaml_path;
                        window.lastGeneratedOutputPath = result.output_path;
                        // Display the generated YAML in the MCP Tools tab
                        displayGeneratedYaml(result.yaml_path, result.converted_count);
                    }
                    // Show deployment modal with proper result object
                    // Ensure output_path and output_file are set for the modal
                    const modalResult = {
                        output_path: result.output_path || result.yaml_path,
                        output_file: result.output_file || result.yaml_file || 'mcp_server_selected.py',
                        converted_count: result.converted_count || 0
                    };
                    showMCPSetupModal(modalResult);
                    btn.innerHTML = '<i class="fas fa-check"></i> Converted!';
                } else {
                    throw new Error(result.error);
                }
            } catch (error) {
                alert('Conversion failed: ' + error.message);
                btn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Failed';
            } finally {
                setTimeout(() => {
                    btn.disabled = false;
                    btn.innerHTML = '<i class="fas fa-magic"></i> Convert Selected';
                }, 2000);
            }
        }

        function toggleDetection(header) {
            const body = header.nextElementSibling;
            const icon = header.querySelector('.fa-chevron-down, .fa-chevron-up');

            if (body.classList.contains('expanded')) {
                body.classList.remove('expanded');
                icon.classList.remove('fa-chevron-up');
                icon.classList.add('fa-chevron-down');
            } else {
                body.classList.add('expanded');
                icon.classList.remove('fa-chevron-down');
                icon.classList.add('fa-chevron-up');
            }
        }

        function updateStats(data) {
            document.getElementById('totalFiles').textContent = data.total_files || 0;
            document.getElementById('apisFound').textContent = data.total_apis || 0;

            // Count Python files
            let pyCount = 0;
            const countPy = (tree) => {
                if (tree.extension === '.py') pyCount++;
                if (tree.children) tree.children.forEach(countPy);
            };
            countPy(data.file_tree);
            document.getElementById('pythonFiles').textContent = pyCount;

            // Update detection intelligence stats
            if (data.intelligence && data.intelligence.detection_summary) {
                const summary = data.intelligence.detection_summary;
                document.getElementById('routesScanned').textContent = summary.total_routes_scanned || 0;
                document.getElementById('apiEndpoints').textContent = summary.api_endpoints_found || 0;
                document.getElementById('webPages').textContent = summary.web_pages_excluded || 0;

                const avgScore = summary.avg_detection_score || 0;
                document.getElementById('avgScore').textContent = avgScore.toFixed(2);
            }
        }

        function showAPICode() {
            if (!projectData || !projectData.api_definitions || projectData.api_definitions.length === 0) {
                alert('No API endpoints found. Please scan the project first.');
                return;
            }

            const modal = document.getElementById('codeModal');
            const treePanel = document.getElementById('codeTreePanel');

            // Filter out framework/infrastructure APIs
            const frameworkKeywords = ['scan-project', 'convert-to-mcp', 'read-file', 'mcp-test', 'mcp-convert'];
            const businessAPIs = projectData.api_definitions.filter(api => {
                return !frameworkKeywords.some(keyword => api.route.includes(keyword));
            });

            // Group APIs by business domain
            const apisByDomain = {};
            businessAPIs.forEach(api => {
                const domain = api.business_domain || 'general';
                if (!apisByDomain[domain]) {
                    apisByDomain[domain] = [];
                }
                apisByDomain[domain].push(api);
            });

            // Build tree HTML
            const sortedDomains = Object.keys(apisByDomain).sort();
            const totalAPIs = businessAPIs.length;
            let treeHTML = `
                <div style="padding: 0.75rem; background: rgba(59, 130, 246, 0.1); border-radius: 6px; margin-bottom: 1rem; font-size: 0.85rem; color: rgba(255, 255, 255, 0.9);">
                    <div style="font-weight: 600; margin-bottom: 0.25rem;"><i class="fas fa-info-circle"></i> Badge Legend</div>
                    <div style="color: rgba(255, 255, 255, 0.8);">
                        <strong>X/Y</strong> = High Quality APIs / Total APIs<br>
                        <span style="font-size: 0.8rem; color: rgba(255, 255, 255, 0.7);">X = APIs with ≥80% MCP suitability score</span>
                    </div>
                    <div id="analysisProgress" style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid rgba(255, 255, 255, 0.2); color: var(--scikiq-light-blue); font-weight: 500;">
                        <i class="fas fa-spinner fa-spin"></i> Analyzing APIs... (0/${totalAPIs})
                    </div>
                </div>
            `;

            sortedDomains.forEach((domain, domainIndex) => {
                const apis = apisByDomain[domain];
                const domainId = `domain-${domain.replace(/\s+/g, '-')}`;

                treeHTML += `
                    <div class="tree-domain">
                        <div class="tree-domain-header" onclick="toggleDomain('${domainId}')">
                            <span><i class="fas fa-folder"></i> ${domain.charAt(0).toUpperCase() + domain.slice(1)}</span>
                            <span class="domain-count" id="badge-${domainIndex}" title="High Score / Total APIs (≥80% / Total)">0/${apis.length}</span>
                        </div>
                        <div class="tree-endpoints" id="${domainId}">
                `;

                apis.forEach((api, apiIndex) => {
                    const endpointId = `endpoint-${domainIndex}-${apiIndex}`;
                    treeHTML += `
                        <div class="tree-endpoint" id="${endpointId}" onclick="showEndpointCode(${domainIndex}, ${apiIndex})">
                            <span class="tree-endpoint-method ${api.methods[0]}">${api.methods[0]}</span>
                            <span class="tree-endpoint-route">${escapeHtml(api.route)}</span>
                        </div>
                    `;
                });

                treeHTML += `
                        </div>
                    </div>
                `;
            });

            treePanel.innerHTML = treeHTML;

            // Store data for later access
            window.apiTreeData = { apisByDomain, sortedDomains, businessAPIs };

            modal.classList.add('show');

            // Auto-expand first domain
            if (sortedDomains.length > 0) {
                toggleDomain(`domain-${sortedDomains[0].replace(/\s+/g, '-')}`);
            }

            // Auto-analyze all endpoints in background to populate badges
            autoAnalyzeAllEndpoints();
        }

        async function autoAnalyzeAllEndpoints() {
            const { apisByDomain, sortedDomains, businessAPIs } = window.apiTreeData;

            console.log('Starting auto-analysis with setTimeout approach...');

            // Initialize domain scores and progress tracking
            window.domainScores = {};
            window.analyzedCount = 0;
            const totalAPIs = businessAPIs.length;

            let globalIndex = 0;

            for (let domainIndex = 0; domainIndex < sortedDomains.length; domainIndex++) {
                const domain = sortedDomains[domainIndex];
                const apis = apisByDomain[domain];

                for (let apiIndex = 0; apiIndex < apis.length; apiIndex++) {
                    const api = apis[apiIndex];
                    const delay = globalIndex * 300; // 300ms between each request

                    setTimeout(async () => {
                        try {
                            console.log(`Analyzing ${api.route}...`);

                            const response = await fetch('/api/analyze-endpoint', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    route: api.route,
                                    method: api.methods[0],
                                    function_name: api.function_name,
                                    function_code: api.function_code,
                                    docstring: api.docstring,
                                    business_domain: api.business_domain
                                })
                            });

                            const result = await response.json();

                            if (result.success && result.mcp_suitability) {
                                const score = result.mcp_suitability.score;
                                console.log(`Got score ${score} for ${api.route} (domain:${domainIndex}, api:${apiIndex})`);

                                // Store score with API index
                                if (!window.domainScores[domainIndex]) {
                                    window.domainScores[domainIndex] = {};
                                }
                                window.domainScores[domainIndex][apiIndex] = score;
                                console.log(`Stored scores for domain ${domainIndex}:`, window.domainScores[domainIndex]);

                                // Update progress counter
                                window.analyzedCount++;
                                const progressEl = document.getElementById('analysisProgress');
                                if (progressEl) {
                                    progressEl.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Analyzing APIs... (${window.analyzedCount}/${totalAPIs})`;
                                }

                                // Color code the tree endpoint
                                const endpointEl = document.getElementById(`endpoint-${domainIndex}-${apiIndex}`);
                                if (endpointEl) {
                                    if (score >= 80) {
                                        endpointEl.classList.add('score-high');
                                    } else {
                                        endpointEl.classList.add('score-low');
                                    }
                                }

                                // Update badge immediately
                                updateDomainBadge(domainIndex);

                                // Mark complete when all done
                                if (window.analyzedCount >= totalAPIs) {
                                    setTimeout(() => {
                                        if (progressEl) {
                                            progressEl.innerHTML = `<i class="fas fa-check-circle"></i> Analysis Complete! (${totalAPIs}/${totalAPIs})`;
                                            progressEl.style.color = '#10B981';
                                        }
                                    }, 500);
                                }
                            }
                        } catch (error) {
                            console.error(`Error analyzing ${api.route}:`, error);
                        }
                    }, delay);

                    globalIndex++;
                }
            }
        }

        function toggleDomain(domainId) {
            const endpoints = document.getElementById(domainId);
            if (endpoints) {
                endpoints.classList.toggle('expanded');
            }
        }

        function showEndpointCode(domainIndex, apiIndex) {
            const { apisByDomain, sortedDomains } = window.apiTreeData;
            const domain = sortedDomains[domainIndex];
            const api = apisByDomain[domain][apiIndex];

            // Remove active class from all endpoints
            document.querySelectorAll('.tree-endpoint').forEach(el => el.classList.remove('active'));

            // Add active class to selected endpoint
            const endpointId = `endpoint-${domainIndex}-${apiIndex}`;
            document.getElementById(endpointId).classList.add('active');

            // Build code display
            const codeContent = document.getElementById('modalCodeContent');
            const codePlaceholder = document.querySelector('.code-display-panel .code-placeholder');

            let codeDisplay = '';
            codeDisplay += `╔${'═'.repeat(78)}╗\n`;
            codeDisplay += `║  ${api.methods[0]} ${api.route}${' '.repeat(75 - api.methods[0].length - api.route.length)}║\n`;
            codeDisplay += `╚${'═'.repeat(78)}╝\n\n`;

            codeDisplay += `${'═'.repeat(80)}\n`;
            codeDisplay += `FUNCTION CODE\n`;
            codeDisplay += `${'═'.repeat(80)}\n\n`;

            if (api.function_code) {
                codeDisplay += api.function_code;
            } else {
                codeDisplay += '// Code not available\n';
            }

            codeContent.textContent = codeDisplay;
            codePlaceholder.style.display = 'none';
            codeContent.style.display = 'block';

            // Build metadata panel
            const metadataPanel = document.getElementById('codeMetadataPanel');
            const metadataPlaceholder = metadataPanel.querySelector('.code-placeholder');

            let metadataHTML = '';

            // Basic Info Section
            metadataHTML += `
                <div class="metadata-section">
                    <div class="metadata-section-title">
                        <i class="fas fa-info-circle"></i> Basic Information
                    </div>
                    <div class="metadata-row">
                        <span class="metadata-label">Route</span>
                        <span class="metadata-value">${escapeHtml(api.route)}</span>
                    </div>
                    <div class="metadata-row">
                        <span class="metadata-label">Method</span>
                        <span class="metadata-value">
                            ${api.methods.map(m => `<span class="metadata-badge badge-info">${m}</span>`).join('')}
                        </span>
                    </div>
                    <div class="metadata-row">
                        <span class="metadata-label">Function</span>
                        <span class="metadata-value">${api.function_name}()</span>
                    </div>
                    <div class="metadata-row">
                        <span class="metadata-label">File Location</span>
                        <span class="metadata-value">${api.file.split('\\').pop()}:${api.line_number}</span>
                    </div>
                    <div class="metadata-row">
                        <span class="metadata-label">Business Domain</span>
                        <span class="metadata-value">
                            <span class="metadata-badge badge-info">${api.business_domain || 'general'}</span>
                        </span>
                    </div>
                    <div class="metadata-row">
                        <span class="metadata-label">Security Level</span>
                        <span class="metadata-value">
                            <span class="metadata-badge ${api.security_level === 'admin' ? 'badge-low' : api.security_level === 'authenticated' ? 'badge-medium' : 'badge-high'}">${api.security_level || 'public'}</span>
                        </span>
                    </div>
                    <div class="metadata-row">
                        <span class="metadata-label">Async</span>
                        <span class="metadata-value">${api.is_async ? 'Yes' : 'No'}</span>
                    </div>
                </div>
            `;

            // Plain English Explanation Section
            metadataHTML += `
                <div class="metadata-section">
                    <div class="metadata-section-title">
                        <i class="fas fa-comment-dots"></i> What This Function Does
                    </div>
                    <div class="plain-english" id="plainEnglish-${domainIndex}-${apiIndex}">
                        <div class="loading-spinner" style="margin: 0 auto;"></div>
                        <p style="text-align: center; margin-top: 0.5rem;">Generating plain English explanation...</p>
                    </div>
                </div>
            `;

            // MCP Tool Suitability Section
            metadataHTML += `
                <div class="metadata-section">
                    <div class="metadata-section-title">
                        <i class="fas fa-robot"></i> MCP Tool Suitability
                    </div>
                    <div id="mcpSuitability-${domainIndex}-${apiIndex}">
                        <div class="loading-spinner" style="margin: 0 auto;"></div>
                        <p style="text-align: center; margin-top: 0.5rem;">Analyzing MCP tool suitability...</p>
                    </div>
                </div>
            `;

            // Documentation Section
            metadataHTML += `
                <div class="metadata-section">
                    <div class="metadata-section-title">
                        <i class="fas fa-book"></i> Documentation
                    </div>
                    <p style="color: rgba(255, 255, 255, 0.8); line-height: 1.6;" id="apiDocstring-${domainIndex}-${apiIndex}">${api.docstring}</p>
                    <button class="doc-action-btn" onclick="generateDocumentation(${domainIndex}, ${apiIndex})" id="genDocBtn-${domainIndex}-${apiIndex}">
                        <i class="fas fa-magic"></i> Generate Enhanced Documentation
                    </button>
                </div>
            `;

            // Detection Analysis Section
            if (api.detection) {
                const score = api.detection.score || 0;
                const threshold = api.detection.threshold || 2;
                const scoreBadge = score >= threshold * 2 ? 'badge-high' : score >= threshold ? 'badge-medium' : 'badge-low';

                metadataHTML += `
                    <div class="metadata-section">
                        <div class="metadata-section-title">
                            <i class="fas fa-brain"></i> Detection Analysis
                        </div>
                        <div class="metadata-row">
                            <span class="metadata-label">Decision</span>
                            <span class="metadata-value">
                                <span class="metadata-badge badge-high">${api.detection.decision || 'API'}</span>
                            </span>
                        </div>
                        <div class="metadata-row">
                            <span class="metadata-label">Confidence Score</span>
                            <span class="metadata-value">
                                <span class="metadata-badge ${scoreBadge}">${score} / ${threshold}</span>
                            </span>
                        </div>
                        <div style="margin-top: 0.8rem;">
                            <div style="color: rgba(255, 255, 255, 0.7); font-size: 0.9rem; margin-bottom: 0.5rem;">
                                <strong>Detection Signals (${api.detection.signals ? api.detection.signals.length : 0})</strong>
                            </div>
                `;

                if (api.detection.signals && api.detection.signals.length > 0) {
                    api.detection.signals.forEach(sig => {
                        const isPositive = sig.verdict === 'API';
                        metadataHTML += `
                            <div class="detection-signal-item ${!isPositive ? 'negative' : ''}">
                                <div class="signal-header">
                                    <span class="signal-type">
                                        <i class="fas ${isPositive ? 'fa-check-circle' : 'fa-times-circle'}"></i>
                                        ${sig.type.replace(/_/g, ' ')}
                                    </span>
                                    <span class="signal-weight">+${sig.weight}</span>
                                </div>
                                <div class="signal-value">${sig.value}</div>
                            </div>
                        `;
                    });
                } else {
                    metadataHTML += '<p style="color: rgba(255, 255, 255, 0.5); font-style: italic;">No signals recorded</p>';
                }

                metadataHTML += `
                        </div>
                    </div>
                `;
            }

            // Parameters Section
            if (api.parameters && api.parameters.length > 0) {
                metadataHTML += `
                    <div class="metadata-section">
                        <div class="metadata-section-title">
                            <i class="fas fa-sliders-h"></i> Parameters (${api.parameters.length})
                        </div>
                `;

                api.parameters.forEach(param => {
                    metadataHTML += `
                        <div class="param-item">
                            <div>
                                <span class="param-name">${param.name}</span>
                                ${param.required ? '<span class="param-required">REQUIRED</span>' : ''}
                            </div>
                            <div style="margin-top: 0.3rem;">
                                <span class="param-type">${param.type || 'any'}</span>
                            </div>
                        </div>
                    `;
                });

                metadataHTML += `</div>`;
            }

            // Request Fields Section
            if (api.request_fields && api.request_fields.length > 0) {
                metadataHTML += `
                    <div class="metadata-section">
                        <div class="metadata-section-title">
                            <i class="fas fa-file-import"></i> Request Body (${api.request_fields.length})
                        </div>
                `;

                api.request_fields.forEach(field => {
                    metadataHTML += `
                        <div class="param-item">
                            <div>
                                <span class="param-name">${field.name}</span>
                                ${field.required ? '<span class="param-required">REQUIRED</span>' : ''}
                            </div>
                            <div style="margin-top: 0.3rem;">
                                <span class="param-type">${field.type || 'any'}</span>
                            </div>
                        </div>
                    `;
                });

                metadataHTML += `</div>`;
            }

            // Confidence Score Section
            if (api.confidence !== undefined) {
                const confidenceBadge = api.confidence >= 0.8 ? 'badge-high' : api.confidence >= 0.6 ? 'badge-medium' : 'badge-low';
                metadataHTML += `
                    <div class="metadata-section">
                        <div class="metadata-section-title">
                            <i class="fas fa-chart-line"></i> Analysis Confidence
                        </div>
                        <div class="metadata-row">
                            <span class="metadata-label">Overall Confidence</span>
                            <span class="metadata-value">
                                <span class="metadata-badge ${confidenceBadge}">${(api.confidence * 100).toFixed(1)}%</span>
                            </span>
                        </div>
                    </div>
                `;
            }

            if (metadataPlaceholder) {
                metadataPlaceholder.style.display = 'none';
            }

            // Set the metadata HTML after the placeholder
            metadataPanel.innerHTML = metadataHTML;

            // Load AI insights asynchronously
            loadAIInsights(domainIndex, apiIndex, api);
        }

        async function loadAIInsights(domainIndex, apiIndex, api) {
            try {
                const response = await fetch('/api/analyze-endpoint', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        route: api.route,
                        method: api.methods[0],
                        function_name: api.function_name,
                        function_code: api.function_code,
                        docstring: api.docstring,
                        business_domain: api.business_domain
                    })
                });

                const data = await response.json();

                if (data.success) {
                    // Update plain English explanation
                    const plainEnglishEl = document.getElementById(`plainEnglish-${domainIndex}-${apiIndex}`);
                    if (plainEnglishEl && data.plain_english) {
                        plainEnglishEl.innerHTML = `<p>${data.plain_english}</p>`;
                    }

                    // Update MCP suitability
                    const mcpSuitEl = document.getElementById(`mcpSuitability-${domainIndex}-${apiIndex}`);
                    if (mcpSuitEl && data.mcp_suitability) {
                        const score = data.mcp_suitability.score;
                        const scoreClass = score >= 80 ? 'mcp-score-high' : 'mcp-score-low';
                        const recommendation = score >= 80 ?
                            '✓ Excellent MCP Tool Candidate' :
                            '⚠ Limited MCP Tool Suitability';

                        mcpSuitEl.innerHTML = `
                            <div class="mcp-suitability">
                                <div class="mcp-score-circle ${scoreClass}">
                                    ${score}%
                                </div>
                                <div class="mcp-recommendation">
                                    <div class="mcp-recommendation-title">${recommendation}</div>
                                    <div class="mcp-recommendation-text">${data.mcp_suitability.reason}</div>
                                </div>
                            </div>
                        `;

                        // Store score for badge update
                        if (!window.domainScores) {
                            window.domainScores = {};
                        }
                        if (!window.domainScores[domainIndex]) {
                            window.domainScores[domainIndex] = [];
                        }
                        window.domainScores[domainIndex].push(score);
                        console.log(`Stored score ${score} for domain ${domainIndex}. Scores:`, window.domainScores[domainIndex]);

                        // Update badge
                        updateDomainBadge(domainIndex);
                    }
                }
            } catch (error) {
                console.error('Error loading AI insights:', error);
                // Show fallback content
                const plainEnglishEl = document.getElementById(`plainEnglish-${domainIndex}-${apiIndex}`);
                if (plainEnglishEl) {
                    plainEnglishEl.innerHTML = '<p style="color: rgba(255, 255, 255, 0.6);">AI analysis unavailable</p>';
                }
            }
        }

        function updateDomainBadge(domainIndex) {
            if (!window.apiTreeData) {
                console.error('window.apiTreeData is not defined');
                return;
            }

            const { apisByDomain, sortedDomains } = window.apiTreeData;
            const domain = sortedDomains[domainIndex];
            const totalAPIs = apisByDomain[domain].length;

            const scoresObj = window.domainScores[domainIndex] || {};
            const scoresArray = Object.values(scoresObj);
            const highScoreCount = scoresArray.filter(score => score >= 80).length;

            const badgeEl = document.getElementById(`badge-${domainIndex}`);
            if (badgeEl) {
                console.log(`Updating badge for domain ${domain}: ${highScoreCount}/${totalAPIs}`, 'Scores:', scoresObj);
                badgeEl.textContent = `${highScoreCount}/${totalAPIs}`;

                // Color code the badge
                badgeEl.classList.remove('badge-high', 'badge-low', 'badge-mixed');

                if (scoresArray.length === totalAPIs) {
                    // All scores received, apply final color
                    const percentage = (highScoreCount / totalAPIs) * 100;
                    if (percentage >= 75) {
                        badgeEl.classList.add('badge-high');
                    } else if (percentage >= 40) {
                        badgeEl.classList.add('badge-mixed');
                    } else {
                        badgeEl.classList.add('badge-low');
                    }
                }
            } else {
                console.error(`Badge element not found: badge-${domainIndex}`);
            }
        }

        async function generateDocumentation(domainIndex, apiIndex) {
            const { apisByDomain, sortedDomains } = window.apiTreeData;
            const domain = sortedDomains[domainIndex];
            const api = apisByDomain[domain][apiIndex];

            const btn = document.getElementById(`genDocBtn-${domainIndex}-${apiIndex}`);
            btn.disabled = true;
            btn.innerHTML = '<span class="loading-spinner"></span> Generating...';

            try {
                const response = await fetch('/api/generate-docstring', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        route: api.route,
                        method: api.methods[0],
                        function_name: api.function_name,
                        function_code: api.function_code,
                        current_docstring: api.docstring
                    })
                });

                const data = await response.json();

                if (data.success && data.docstring) {
                    // Show confirmation dialog
                    const confirmed = confirm(`Generated Documentation:\n\n${data.docstring}\n\nWould you like to update the function with this documentation?`);

                    if (confirmed) {
                        // Update the display
                        const docEl = document.getElementById(`apiDocstring-${domainIndex}-${apiIndex}`);
                        if (docEl) {
                            docEl.textContent = data.docstring;
                        }

                        // Here you would normally call an endpoint to update the actual file
                        // For now, just show success
                        btn.innerHTML = '<i class="fas fa-check"></i> Documentation Updated!';
                        setTimeout(() => {
                            btn.innerHTML = '<i class="fas fa-magic"></i> Generate Enhanced Documentation';
                            btn.disabled = false;
                        }, 2000);
                    } else {
                        btn.innerHTML = '<i class="fas fa-magic"></i> Generate Enhanced Documentation';
                        btn.disabled = false;
                    }
                } else {
                    throw new Error(data.error || 'Failed to generate documentation');
                }
            } catch (error) {
                console.error('Error generating documentation:', error);
                alert('Failed to generate documentation: ' + error.message);
                btn.innerHTML = '<i class="fas fa-magic"></i> Generate Enhanced Documentation';
                btn.disabled = false;
            }
        }

        function closeCodeModal() {
            const modal = document.getElementById('codeModal');
            modal.classList.remove('show');
        }

        // Close modal when clicking outside
        document.addEventListener('click', (e) => {
            const modal = document.getElementById('codeModal');
            if (e.target === modal) {
                closeCodeModal();
            }
        });

        // Close modal with Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeCodeModal();
            }
        });

        async function generateMCP() {
            const btn = document.getElementById('generateBtn');
            btn.disabled = true;
            btn.innerHTML = '<div class="spinner"></div> Generating...';

            try {
                const response = await fetch('/api/mcp-convert', {
                    method: 'POST'
                });

                mcpData = await response.json();

                // Render MCP tools
                renderMCPTools(mcpData.tools);

                // Show documentation
                if (projectData.api_documentation) {
                    const docsContainer = document.getElementById('documentationContent');
                    docsContainer.innerHTML = marked.parse(projectData.api_documentation);
                }

                // Update stats
                document.getElementById('mcpTools').textContent = mcpData.tools.length;

                // Enable test button
                document.getElementById('testBtn').disabled = false;

                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-check"></i> MCP Generated';

                setTimeout(() => {
                    btn.innerHTML = '<i class="fas fa-cogs"></i> Generate MCP Tools';
                }, 2000);

            } catch (error) {
                console.error('MCP generation error:', error);
                btn.disabled = false;
                btn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Failed';
            }
        }

        function renderMCPTools(tools) {
            const container = document.getElementById('mcpToolsList');
            container.innerHTML = '';

            tools.forEach((tool, index) => {
                const card = document.createElement('div');
                card.className = 'api-card';

                card.innerHTML = `
                    <div style="display: flex; align-items: center; margin-bottom: 0.8rem;">
                        <div style="background: linear-gradient(135deg, var(--anthropic-orange), var(--anthropic-purple)); width: 40px; height: 40px; border-radius: 10px; display: flex; align-items: center; justify-content: center; margin-right: 1rem;">
                            <i class="fas fa-tools" style="font-size: 1.2rem;"></i>
                        </div>
                        <div>
                            <div style="font-family: 'Fira Code', monospace; font-weight: 700; color: var(--anthropic-orange);">
                                ${tool.name}
                            </div>
                            <div style="font-size: 0.85rem; color: rgba(255, 255, 255, 0.6);">
                                ${tool.endpoint}
                            </div>
                        </div>
                    </div>
                    <div style="color: rgba(255, 255, 255, 0.8); margin-bottom: 0.8rem;">
                        ${tool.description}
                    </div>
                    <div style="background: rgba(0, 0, 0, 0.3); padding: 0.8rem; border-radius: 8px; font-size: 0.85rem;">
                        <strong style="color: var(--scikiq-light-blue);">Input Schema:</strong>
                        <div style="margin-top: 0.5rem; color: rgba(255, 255, 255, 0.7);">
                            ${Object.keys(tool.inputSchema.properties || {}).length} parameters
                        </div>
                    </div>
                `;

                container.appendChild(card);
            });
        }

        function switchTab(tabName) {
            // Update tab buttons
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            event.target.closest('.tab').classList.add('active');

            // Update tab content
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            const tabContent = document.getElementById(`${tabName}-tab`);
            if (tabContent) {
                tabContent.classList.add('active');
            }
        }

        function copyCode() {
            const code = document.getElementById('codeContent').textContent;
            navigator.clipboard.writeText(code);
        }

        function downloadDocs() {
            if (!projectData || !projectData.api_documentation) return;

            const blob = new Blob([projectData.api_documentation], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'glic_api_documentation.md';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }

        function testWithClaude() {
            if (!mcpData) return;

            alert('To test with Claude:\n\n1. Download the generated MCP server\n2. Configure Claude Desktop (see setup instructions)\n3. Restart Claude and look for the hammer icon 🔨\n\nYour SCIKIQ MCP tools will be available!');

            window.open('https://modelcontextprotocol.io/quickstart', '_blank');
        }

        // Update bulk analyze button text based on selected threshold and max APIs
        function updateBulkAnalyzeButton() {
            const threshold = document.getElementById('confidenceThreshold').value;
            const maxApisSelection = document.getElementById('maxApisToAnalyze').value;
            const btn = document.getElementById('bulkAnalyzeBtn');
            const icon = '<i class="fas fa-chart-line"></i>';

            // Calculate number of APIs that will be analyzed
            let apiCount = 0;
            if (projectData && projectData.api_definitions) {
                let apisToAnalyze;

                if (projectSourceType === 'swagger') {
                    apisToAnalyze = projectData.api_definitions;
                } else {
                    // Filter business APIs for folder scans
                    apisToAnalyze = projectData.api_definitions.filter(api => {
                        const route = api.route.toLowerCase();
                        const isBusinessAPI = (
                            route.includes('/products') ||
                            route.includes('/quote/') ||
                            route.includes('/claims') ||
                            route.includes('/policy') ||
                            route.includes('/customer')
                        );
                        const isFrameworkAPI = (
                            route.includes('scan') ||
                            route.includes('convert') ||
                            route.includes('analyze') ||
                            route.includes('mcp') ||
                            route.includes('read-file') ||
                            route.includes('docstring')
                        );
                        return isBusinessAPI && !isFrameworkAPI;
                    });
                }

                // Apply max APIs limit
                const maxApis = maxApisSelection === 'all' ? apisToAnalyze.length : parseInt(maxApisSelection);
                apiCount = Math.min(apisToAnalyze.length, maxApis);
            }

            const countText = apiCount > 0 ? ` (${apiCount} APIs)` : '';
            btn.innerHTML = `${icon} Bulk Analyze ${threshold}%+${countText}`;
        }

        // Bulk Analysis Function
        async function bulkAnalyzeAPIs() {
            if (!projectData || !projectData.api_definitions) {
                alert('Please scan the project first');
                return;
            }

            // Filter APIs based on source type and confidence threshold
            let apisToAnalyze;

            if (projectSourceType === 'swagger') {
                // For Swagger imports, use all APIs (no filtering needed)
                apisToAnalyze = projectData.api_definitions;
            } else {
                // For codebase scans, trust the intelligent analyzer
                // It already filtered out web pages and non-API routes
                // Just exclude framework/MCP tool routes from THIS app
                apisToAnalyze = projectData.api_definitions.filter(api => {
                    const route = api.route.toLowerCase();

                    // Exclude MCP Studio's own framework routes
                    const isFrameworkAPI = (
                        route.includes('/api/scan') ||
                        route.includes('/api/convert') ||
                        route.includes('/api/analyze') ||
                        route.includes('/api/batch-convert') ||
                        route.includes('/api/read-file') ||
                        route.includes('/api/parse-swagger') ||
                        route.includes('/health') ||
                        route.includes('/about') ||
                        route === '/'
                    );

                    // Include all user APIs that aren't our framework APIs
                    return !isFrameworkAPI;
                });

                if (apisToAnalyze.length === 0) {
                    alert('No business APIs found. The scanned project appears to contain only framework/infrastructure routes.\n\nPlease scan a different project folder with your business APIs.');
                    return;
                }
            }

            const totalAPIs = apisToAnalyze.length;

            // Get selected max APIs from UI
            const maxApisSelection = document.getElementById('maxApisToAnalyze').value;
            const maxAPIs = maxApisSelection === 'all' ? totalAPIs : parseInt(maxApisSelection);

            // Warn if too many APIs (only if not selecting "all")
            if (maxApisSelection !== 'all' && totalAPIs > maxAPIs) {
                const filteredCount = projectData.api_definitions.length - apisToAnalyze.length;
                const filterMsg = filteredCount > 0 ? ` (filtered out ${filteredCount} framework APIs)` : '';
                const proceed = confirm(`Found ${totalAPIs} APIs${filterMsg}.\n\nThis will analyze only the first ${maxAPIs} APIs.\n\n💡 TIP: Select "All APIs" to analyze everything, or use "Analyze Selected" for specific domains.\n\nContinue with ${maxAPIs} APIs?`);
                if (!proceed) return;
            } else if (maxApisSelection === 'all' && totalAPIs > 10) {
                // Warning for analyzing all APIs if it's a large number
                const proceed = confirm(`This will analyze ALL ${totalAPIs} APIs.\n\n⚠️  This may take several minutes and consume API credits.\n\n💡 TIP: Consider using a smaller number first to test.\n\nContinue with all ${totalAPIs} APIs?`);
                if (!proceed) return;
            }

            const btn = document.getElementById('bulkAnalyzeBtn');
            btn.disabled = true;
            const actualMaxAPIs = Math.min(totalAPIs, maxAPIs);
            btn.innerHTML = '<div class="spinner"></div> Analyzing APIs (0/' + actualMaxAPIs + ')...';

            try {
                // Create abort controller for timeout (dynamic based on API count)
                const controller = new AbortController();
                const baseTimeout = 60000; // 1 minute base
                const perApiTimeout = 15000; // 15 seconds per API
                const dynamicTimeout = Math.max(baseTimeout, actualMaxAPIs * perApiTimeout);
                const timeoutId = setTimeout(() => controller.abort(), dynamicTimeout);

                // Get dynamic confidence threshold
                const selectedThreshold = parseInt(document.getElementById('confidenceThreshold').value);

                const response = await fetch('/api/bulk-analyze-apis', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        endpoints: apisToAnalyze,
                        min_confidence: selectedThreshold,
                        max_apis: actualMaxAPIs
                    }),
                    signal: controller.signal
                });

                clearTimeout(timeoutId);

                if (!response.ok) {
                    throw new Error(`Server returned ${response.status}: ${response.statusText}`);
                }

                const result = await response.json();

                if (result.success) {
                    // Update projectData with MCP scores
                    if (result.all_analyzed_apis) {
                        result.all_analyzed_apis.forEach((analyzedApi, idx) => {
                            if (projectData.api_definitions[idx]) {
                                // Add mcp_suitability_score from analysis
                                projectData.api_definitions[idx].mcp_suitability_score = analyzedApi.analysis.mcp_score;
                                projectData.api_definitions[idx].analysis = analyzedApi.analysis;
                            }
                        });

                        // Re-render APIs with updated scores
                        renderAPIs(projectData.api_definitions);
                    }

                    // Store high confidence APIs FIRST before showing modal
                    window.highConfidenceAPIs = result.high_confidence_apis;

                    // Show summary modal
                    showBulkAnalysisSummary(result);

                    // Enable convert button if it exists
                    const convertHighBtn = document.getElementById('convertHighBtn');
                    if (convertHighBtn) {
                        convertHighBtn.disabled = false;
                    }

                    btn.disabled = false;
                    btn.innerHTML = '<i class="fas fa-check"></i> Analysis Complete';

                    setTimeout(() => {
                        updateBulkAnalyzeButton();
                    }, 3000);
                } else {
                    throw new Error(result.error || 'Analysis failed');
                }

            } catch (error) {
                console.error('Bulk analysis error:', error);

                let errorMsg = 'Bulk analysis failed';
                if (error.name === 'AbortError') {
                    errorMsg = 'Analysis timed out after 2 minutes.\n\n💡 TIP: Try selecting fewer APIs or use "Analyze Selected" on individual domains.';
                } else if (error.message.includes('Failed to fetch')) {
                    errorMsg = 'Connection lost during analysis.\n\nThe server may have taken too long to respond.\n\n💡 TIP: Try analyzing fewer APIs at once using "Analyze Selected".';
                } else {
                    errorMsg = `Analysis failed: ${error.message}`;
                }

                alert(errorMsg);
                btn.disabled = false;
                updateBulkAnalyzeButton();
            }
        }

        function showBulkAnalysisSummary(result) {
            const summary = result.summary;
            const apis = result.high_confidence_apis;

            let summaryHTML = `
                <div style="background: rgba(16, 185, 129, 0.1); border: 2px solid var(--success-green); border-radius: 12px; padding: 2rem; margin: 2rem;">
                    <h3 style="color: var(--success-green); margin-bottom: 1.5rem;">
                        <i class="fas fa-check-circle"></i> Bulk Analysis Complete
                    </h3>

                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;">
                        <div style="background: rgba(255, 255, 255, 0.05); padding: 1.5rem; border-radius: 8px; text-align: center;">
                            <div style="font-size: 2.5rem; font-weight: 700; color: var(--scikiq-light-blue);">${summary.total_analyzed}</div>
                            <div style="color: rgba(255, 255, 255, 0.7); margin-top: 0.5rem;">Total APIs Analyzed</div>
                        </div>
                        <div style="background: rgba(255, 255, 255, 0.05); padding: 1.5rem; border-radius: 8px; text-align: center;">
                            <div style="font-size: 2.5rem; font-weight: 700; color: var(--success-green);">${summary.high_confidence_count}</div>
                            <div style="color: rgba(255, 255, 255, 0.7); margin-top: 0.5rem;">High Confidence (80%+)</div>
                        </div>
                        <div style="background: rgba(255, 255, 255, 0.05); padding: 1.5rem; border-radius: 8px; text-align: center;">
                            <div style="font-size: 2.5rem; font-weight: 700; color: var(--anthropic-purple);">${summary.average_score}%</div>
                            <div style="color: rgba(255, 255, 255, 0.7); margin-top: 0.5rem;">Average Score</div>
                        </div>
                    </div>

                    <h4 style="color: var(--scikiq-light-blue); margin-bottom: 1rem;">
                        <i class="fas fa-star"></i> Top APIs Ready for MCP Conversion (${apis.length})
                    </h4>

                    <div style="max-height: 400px; overflow-y: auto;">
            `;

            apis.forEach((api, index) => {
                const analysis = api.analysis;
                summaryHTML += `
                    <div style="background: rgba(255, 255, 255, 0.03); border-left: 3px solid var(--success-green); padding: 1rem; margin-bottom: 1rem; border-radius: 8px;">
                        <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                            <div>
                                <span style="background: var(--success-green); color: white; padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.8rem; font-weight: 600;">${analysis.mcp_score}%</span>
                                <strong style="color: var(--scikiq-light-blue); margin-left: 0.5rem;">${api.methods[0]}</strong>
                                <span style="color: rgba(255, 255, 255, 0.9);">${api.route}</span>
                            </div>
                        </div>
                        <div style="color: rgba(255, 255, 255, 0.7); font-size: 0.9rem; margin-top: 0.5rem;">
                            ${analysis.plain_english}
                        </div>
                        ${analysis.strengths && analysis.strengths.length > 0 ? `
                            <div style="margin-top: 0.5rem; font-size: 0.85rem;">
                                <span style="color: var(--success-green);">✓</span> ${analysis.strengths.slice(0, 2).join(', ')}
                            </div>
                        ` : ''}
                    </div>
                `;
            });

            summaryHTML += `
                    </div>

                    <div style="margin-top: 1.5rem;">
                        <button onclick="convertHighConfidenceAPIs()" style="width: 100%; padding: 1.2rem; background: linear-gradient(135deg, var(--success-green), #059669); border: none; border-radius: 8px; color: white; font-weight: 600; cursor: pointer; font-size: 1.1rem; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3); transition: all 0.3s ease;">
                            <i class="fas fa-magic"></i> Convert ${apis.length} APIs to MCP Tools
                        </button>
                        <p style="text-align: center; color: rgba(255, 255, 255, 0.6); font-size: 0.9rem; margin-top: 1rem;">
                            <i class="fas fa-info-circle"></i> After conversion, you'll see deployment options for local and online setup
                        </p>
                    </div>
                </div>
            `;

            // Create modal
            const modal = document.createElement('div');
            modal.style.cssText = 'position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.8); z-index: 10000; display: flex; align-items: center; justify-content: center; padding: 2rem;';
            modal.innerHTML = `
                <div style="background: linear-gradient(135deg, rgba(0, 48, 135, 0.95), rgba(26, 31, 58, 0.95)); border-radius: 16px; max-width: 900px; width: 100%; max-height: 90vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5); position: relative;">
                    <button onclick="this.closest('[style*=fixed]').remove()" style="position: absolute; top: 1rem; right: 1rem; background: rgba(255, 255, 255, 0.2); border: none; color: white; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; transition: all 0.3s ease; z-index: 10;" onmouseover="this.style.background='rgba(255, 255, 255, 0.3)'" onmouseout="this.style.background='rgba(255, 255, 255, 0.2)'">
                        <i class="fas fa-times"></i>
                    </button>
                    ${summaryHTML}
                </div>
            `;

            document.body.appendChild(modal);
        }

        async function convertHighConfidenceAPIs() {
            if (!window.highConfidenceAPIs || window.highConfidenceAPIs.length === 0) {
                alert('No high-confidence APIs found. Please run bulk analysis first.');
                return;
            }

            // Find the convert button in the modal
            const convertBtn = event ? event.target : document.querySelector('button[onclick*="convertHighConfidenceAPIs"]');
            if (convertBtn) {
                convertBtn.disabled = true;
                convertBtn.innerHTML = '<div class="spinner"></div> Converting...';
            }

            try {
                // Get base URL from either Swagger config or folder scan config
                let baseUrl = '';
                if (projectSourceType === 'swagger' && selectedSwaggerConfig.api_base_url) {
                    baseUrl = selectedSwaggerConfig.api_base_url;
                } else if (selectedProjectConfig.api_base_url) {
                    baseUrl = selectedProjectConfig.api_base_url;
                } else {
                    // Fallback: try to read from input field
                    const baseUrlInput = document.getElementById('baseUrl');
                    baseUrl = baseUrlInput ? baseUrlInput.value : '';
                }

                // Get server name from input field
                const serverNameInput = document.getElementById('apiName');
                const serverName = serverNameInput ? serverNameInput.value : 'scikiq-mcp-autoAPI';

                const response = await fetch('/api/batch-convert-to-mcp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        endpoints: window.highConfidenceAPIs,
                        output_file: 'mcp_server_high_confidence.py',
                        base_url: baseUrl,
                        server_name: serverName
                    })
                });

                const result = await response.json();

                if (result.success) {
                    // Close the bulk analysis modal first
                    const bulkAnalysisModal = document.querySelector('[style*="position: fixed"][style*="z-index: 10000"]');
                    if (bulkAnalysisModal) {
                        bulkAnalysisModal.remove();
                    }

                    // Store yaml_path and base URL for later auto-deploy
                    window.lastGeneratedYamlPath = result.yaml_path;
                    window.currentApiDomain = baseUrl;  // Store API domain for server naming

                    // Display the generated YAML in the MCP Tools tab
                    displayGeneratedYaml(result.yaml_path, result.converted_count);

                    // Show detailed setup modal instead of simple alert
                    showMCPSetupModal(result);

                    // Enable test button if it exists
                    const testBtn = document.getElementById('testBtn');
                    if (testBtn) {
                        testBtn.disabled = false;
                    }
                } else {
                    throw new Error(result.error || 'Conversion failed');
                }

            } catch (error) {
                console.error('Conversion error:', error);
                alert('Conversion failed: ' + error.message);
                if (convertBtn) {
                    convertBtn.disabled = false;
                    convertBtn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Failed - Try Again';
                }
            }
        }

        // YAML display functions for MCP Tools tab
        async function displayGeneratedYaml(yamlPath, toolCount) {
            try {
                const response = await fetch('/api/read-file', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ file_path: yamlPath })
                });

                const result = await response.json();

                if (result.success) {
                    // Store the content for copy/download
                    window.generatedYamlContent = result.content;
                    window.generatedYamlPath = yamlPath;
                    // Store output path if available (for deployment)
                    if (!window.lastGeneratedOutputPath) {
                        // Extract directory from YAML path and construct loader path
                        const pathParts = yamlPath.replace(/\\/g, '/').split('/');
                        pathParts.pop(); // Remove YAML filename
                        const serverDir = pathParts.join('/');
                        window.lastGeneratedOutputPath = serverDir + '/mcp_server_loader.py';
                    }

                    // Get filename from path
                    const fileName = yamlPath.split('/').pop().split('\\').pop();

                    // Hide placeholder, show YAML content
                    document.getElementById('mcpToolsList').style.display = 'none';
                    document.getElementById('mcpYamlContent').style.display = 'block';

                    // Update filename and tool count
                    document.getElementById('yamlFileName').textContent = fileName;
                    document.getElementById('yamlToolCount').textContent = `${toolCount} tools defined`;

                    // Apply syntax highlighting to YAML
                    const highlightedYaml = highlightYamlSyntax(result.content);
                    document.getElementById('yamlCodeContent').innerHTML = highlightedYaml;

                    // Show copy/download/deploy buttons
                    document.getElementById('copyYamlBtn').style.display = 'inline-flex';
                    document.getElementById('downloadYamlBtn').style.display = 'inline-flex';
                    document.getElementById('deployYamlBtn').style.display = 'inline-flex';

                    // Update MCP Tools stat
                    document.getElementById('mcpTools').textContent = toolCount;

                    // Switch to MCP Tools tab
                    switchToMcpTab();

                    // Auto-generate documentation from YAML
                    generateDocumentationFromYaml(result.content, toolCount);
                }
            } catch (error) {
                console.error('Error loading YAML:', error);
            }
        }

        // Generate documentation from YAML content
        async function generateDocumentationFromYaml(yamlContent, toolCount) {
            const docsContainer = document.getElementById('documentationContent');

            try {
                // Show loading state
                docsContainer.innerHTML = `
                    <div class="text-center" style="padding: 3rem; color: rgba(255, 255, 255, 0.7);">
                        <div class="loading-spinner" style="width: 40px; height: 40px; border: 3px solid rgba(255, 255, 255, 0.2); border-top-color: var(--anthropic-orange); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 1rem;"></div>
                        <div>Generating documentation for ${toolCount} tools...</div>
                    </div>
                `;

                const response = await fetch('/api/generate-yaml-documentation', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ yaml_content: yamlContent })
                });

                const result = await response.json();

                if (result.success && result.documentation) {
                    // Store documentation for download
                    window.generatedDocumentation = result.documentation;

                    // Render markdown documentation with syntax highlighting
                    const renderedDoc = renderMarkdownDoc(result.documentation);

                    docsContainer.innerHTML = `
                        <div style="margin-bottom: 1rem; display: flex; justify-content: flex-end; gap: 0.5rem;">
                            <button onclick="copyDocumentation()" class="action-btn" style="padding: 0.5rem 1rem; font-size: 0.85rem; background: rgba(255, 255, 255, 0.1);">
                                <i class="fas fa-copy"></i> Copy
                            </button>
                            <button onclick="downloadDocumentation()" class="action-btn" style="padding: 0.5rem 1rem; font-size: 0.85rem; background: linear-gradient(135deg, var(--anthropic-orange), #CC5500);">
                                <i class="fas fa-download"></i> Download MD
                            </button>
                        </div>
                        <div class="markdown-content" style="background: rgba(0, 0, 0, 0.3); border-radius: 8px; padding: 1.5rem; max-height: 600px; overflow-y: auto;">
                            ${renderedDoc}
                        </div>
                    `;
                } else {
                    throw new Error(result.error || 'Failed to generate documentation');
                }
            } catch (error) {
                console.error('Error generating documentation:', error);
                docsContainer.innerHTML = `
                    <div class="text-center" style="padding: 3rem; color: rgba(255, 255, 255, 0.5);">
                        <div><i class="fas fa-exclamation-triangle" style="font-size: 2rem; color: #EF4444; margin-bottom: 1rem;"></i></div>
                        <div>Failed to generate documentation: ${error.message}</div>
                        <button onclick="generateDocumentationFromYaml(window.generatedYamlContent, document.getElementById('mcpTools').textContent)" style="margin-top: 1rem; padding: 0.5rem 1rem; background: var(--anthropic-orange); border: none; border-radius: 6px; color: white; cursor: pointer;">
                            <i class="fas fa-redo"></i> Retry
                        </button>
                    </div>
                `;
            }
        }

        // Simple markdown renderer
        function renderMarkdownDoc(markdown) {
            return markdown
                // Headers
                .replace(/^### (.*$)/gm, '<h3 style="color: var(--scikiq-light-blue); margin: 1.5rem 0 0.5rem; font-size: 1.1rem;">$1</h3>')
                .replace(/^## (.*$)/gm, '<h2 style="color: var(--anthropic-orange); margin: 1.5rem 0 0.75rem; font-size: 1.3rem; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 0.5rem;">$1</h2>')
                .replace(/^# (.*$)/gm, '<h1 style="color: white; margin: 0 0 1rem; font-size: 1.6rem;">$1</h1>')
                // Bold
                .replace(/\*\*(.*?)\*\*/g, '<strong style="color: #E0E0E0;">$1</strong>')
                // Italic
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                // Code blocks
                .replace(/```json\n([\s\S]*?)```/g, '<pre style="background: rgba(0,0,0,0.4); padding: 1rem; border-radius: 6px; overflow-x: auto; font-family: \'Fira Code\', monospace; font-size: 0.85rem; color: #10B981; margin: 0.5rem 0;">$1</pre>')
                .replace(/```([\s\S]*?)```/g, '<pre style="background: rgba(0,0,0,0.4); padding: 1rem; border-radius: 6px; overflow-x: auto; font-family: \'Fira Code\', monospace; font-size: 0.85rem; color: #E0E0E0; margin: 0.5rem 0;">$1</pre>')
                // Inline code
                .replace(/`([^`]+)`/g, '<code style="background: rgba(0,0,0,0.3); padding: 0.2rem 0.4rem; border-radius: 4px; font-family: \'Fira Code\', monospace; font-size: 0.85rem; color: var(--anthropic-orange);">$1</code>')
                // Tables
                .replace(/\|(.+)\|/g, function(match) {
                    if (match.includes('---')) {
                        return ''; // Skip separator row
                    }
                    const cells = match.split('|').filter(c => c.trim());
                    const isHeader = match.includes('Parameter') || match.includes('Type');
                    const cellTag = isHeader ? 'th' : 'td';
                    const cellStyle = isHeader
                        ? 'style="padding: 0.5rem; text-align: left; background: rgba(255,255,255,0.1); color: var(--scikiq-light-blue); font-weight: 600;"'
                        : 'style="padding: 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.1);"';
                    return '<tr>' + cells.map(c => `<${cellTag} ${cellStyle}>${c.trim()}</${cellTag}>`).join('') + '</tr>';
                })
                // Wrap tables
                .replace(/(<tr>.*<\/tr>\n?)+/g, '<table style="width: 100%; border-collapse: collapse; margin: 0.5rem 0; font-size: 0.9rem;">$&</table>')
                // Lists
                .replace(/^- (.*$)/gm, '<li style="margin: 0.3rem 0; color: rgba(255,255,255,0.8);">$1</li>')
                .replace(/(<li.*<\/li>\n?)+/g, '<ul style="margin: 0.5rem 0; padding-left: 1.5rem;">$&</ul>')
                // Numbered lists
                .replace(/^\d+\. \[(.*?)\]\(.*?\)/gm, '<li style="margin: 0.3rem 0;"><a href="#" style="color: var(--scikiq-light-blue); text-decoration: none;">$1</a></li>')
                // Horizontal rule
                .replace(/^---$/gm, '<hr style="border: none; border-top: 1px solid rgba(255,255,255,0.1); margin: 1.5rem 0;">')
                // Line breaks
                .replace(/\n\n/g, '<br><br>')
                .replace(/\n/g, '<br>');
        }

        // Copy documentation to clipboard
        function copyDocumentation() {
            if (window.generatedDocumentation) {
                navigator.clipboard.writeText(window.generatedDocumentation).then(() => {
                    const btns = document.querySelectorAll('.action-btn');
                    btns.forEach(btn => {
                        if (btn.textContent.includes('Copy')) {
                            const originalHTML = btn.innerHTML;
                            btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
                            btn.style.background = 'var(--success-green)';
                            setTimeout(() => {
                                btn.innerHTML = originalHTML;
                                btn.style.background = 'rgba(255, 255, 255, 0.1)';
                            }, 2000);
                        }
                    });
                });
            }
        }

        // Download documentation as markdown file
        function downloadDocumentation() {
            if (window.generatedDocumentation) {
                const fileName = window.generatedYamlPath
                    ? window.generatedYamlPath.split('/').pop().split('\\').pop().replace('.yaml', '_documentation.md').replace('.yml', '_documentation.md')
                    : 'mcp_documentation.md';

                const blob = new Blob([window.generatedDocumentation], { type: 'text/markdown' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = fileName;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }
        }

        function highlightYamlSyntax(yaml) {
            // Simple YAML syntax highlighting
            return yaml
                .replace(/^(\s*)(#.*)$/gm, '$1<span style="color: #6a9955;">$2</span>') // Comments
                .replace(/^(\s*)([a-zA-Z_][a-zA-Z0-9_]*)(:)/gm, '$1<span style="color: #9cdcfe;">$2</span><span style="color: #d4d4d4;">$3</span>') // Keys
                .replace(/:\s*("[^"]*")/g, ': <span style="color: #ce9178;">$1</span>') // String values in quotes
                .replace(/:\s*('[^']*')/g, ': <span style="color: #ce9178;">$1</span>') // String values in single quotes
                .replace(/:\s*(true|false)/gi, ': <span style="color: #569cd6;">$1</span>') // Booleans
                .replace(/:\s*(\d+\.?\d*)/g, ': <span style="color: #b5cea8;">$1</span>') // Numbers
                .replace(/^(\s*-\s)/gm, '<span style="color: #d4d4d4;">$1</span>'); // List items
        }

        function switchToMcpTab() {
            // Update tab buttons
            document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
            const mcpTabBtn = document.querySelector('.tab[onclick*="mcp"]');
            if (mcpTabBtn) mcpTabBtn.classList.add('active');

            // Update tab content
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
            const mcpTab = document.getElementById('mcp-tab');
            if (mcpTab) mcpTab.classList.add('active');
        }

        function copyYamlContent() {
            if (window.generatedYamlContent) {
                navigator.clipboard.writeText(window.generatedYamlContent).then(() => {
                    const btn = document.getElementById('copyYamlBtn');
                    const originalHTML = btn.innerHTML;
                    btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
                    btn.style.background = 'var(--success-green)';
                    setTimeout(() => {
                        btn.innerHTML = originalHTML;
                        btn.style.background = 'rgba(255, 255, 255, 0.1)';
                    }, 2000);
                });
            }
        }

        function downloadYamlFile() {
            if (window.generatedYamlContent && window.generatedYamlPath) {
                const fileName = window.generatedYamlPath.split('/').pop().split('\\').pop();
                const blob = new Blob([window.generatedYamlContent], { type: 'text/yaml' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = fileName;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }
        }

        // Function to show deployment modal from MCP Tools tab
        function showDeploymentModalFromMCPTab() {
            if (!window.generatedYamlPath) {
                alert('No MCP server file found. Please convert APIs to MCP tools first.');
                return;
            }

            // Construct result object from stored paths
            const yamlPath = window.generatedYamlPath;
            const outputPath = window.lastGeneratedOutputPath || yamlPath;
            const fileName = outputPath.split('/').pop().split('\\').pop();
            const toolCount = parseInt(document.getElementById('mcpTools').textContent) || 0;

            const result = {
                output_path: outputPath,
                output_file: fileName,
                converted_count: toolCount
            };

            showMCPSetupModal(result);
        }

        function showMCPSetupModal(result) {
            // Use the actual output_path from backend response instead of hardcoded path
            const fullPath = result.output_path || '';
            const filename = result.output_file;
            const toolCount = result.converted_count;

            const modalHTML = `
                <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.9); z-index: 10000; display: flex; align-items: center; justify-content: center; padding: 2rem;">
                    <div style="background: linear-gradient(135deg, rgba(0, 48, 135, 0.98), rgba(26, 31, 58, 0.98)); border: 2px solid var(--scikiq-light-blue); border-radius: 16px; max-width: 900px; width: 100%; max-height: 90vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.8);">

                        <!-- Header -->
                        <div style="background: linear-gradient(135deg, var(--success-green), #059669); padding: 2rem; border-radius: 14px 14px 0 0; position: relative;">
                            <button onclick="this.closest('[style*=fixed]').remove()" style="position: absolute; top: 1rem; right: 1rem; background: rgba(255, 255, 255, 0.2); border: none; color: white; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; transition: all 0.3s ease;" onmouseover="this.style.background='rgba(255, 255, 255, 0.3)'" onmouseout="this.style.background='rgba(255, 255, 255, 0.2)'">
                                <i class="fas fa-times"></i>
                            </button>
                            <h2 style="margin: 0; color: white; font-size: 1.8rem;">
                                <i class="fas fa-check-circle"></i> MCP Server Generated Successfully!
                            </h2>
                            <p style="margin: 0.5rem 0 0 0; color: rgba(255, 255, 255, 0.9); font-size: 1.1rem;">
                                ${toolCount} APIs converted to MCP tools
                            </p>
                        </div>

                        <!-- Body -->
                        <div style="padding: 2rem;">

                            <!-- Deployment Options -->
                            <div style="margin-bottom: 2rem;">
                                <h3 style="color: var(--scikiq-light-blue); margin-bottom: 1rem;">
                                    <i class="fas fa-rocket"></i> Deploy Your MCP Server
                                </h3>
                                <p style="color: rgba(255, 255, 255, 0.7); margin-bottom: 1.5rem;">
                                    Choose how you want to deploy your MCP server
                                </p>

                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem;">
                                    <!-- Local Deployment -->
                                    <div style="background: rgba(16, 185, 129, 0.1); border: 2px solid var(--success-green); border-radius: 12px; padding: 1.5rem; text-align: center;">
                                        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">💻</div>
                                        <h4 style="color: white; margin: 0 0 0.5rem 0;">Local Deployment</h4>
                                        <p style="color: rgba(255, 255, 255, 0.7); font-size: 0.9rem; margin-bottom: 1rem;">
                                            Deploy to your local Claude Desktop
                                        </p>
                                        <button onclick="deployMCPLocal('${fullPath}', '${filename}')" style="width: 100%; padding: 0.8rem; background: var(--success-green); border: none; border-radius: 6px; color: white; font-weight: 600; cursor: pointer;">
                                            <i class="fas fa-desktop"></i> Deploy Locally
                                        </button>
                                    </div>

                                    <!-- Online Deployment -->
                                    <div style="background: rgba(0, 163, 224, 0.1); border: 2px solid var(--scikiq-light-blue); border-radius: 12px; padding: 1.5rem; text-align: center;">
                                        <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">☁️</div>
                                        <h4 style="color: white; margin: 0 0 0.5rem 0;">Online Deployment</h4>
                                        <p style="color: rgba(255, 255, 255, 0.7); font-size: 0.9rem; margin-bottom: 1rem;">
                                            Deploy to AWS, Azure, or Remote Server
                                        </p>
                                        <button onclick="showOnlineDeploymentModal('${fullPath}', '${filename}')" style="width: 100%; padding: 0.8rem; background: var(--scikiq-light-blue); border: none; border-radius: 6px; color: white; font-weight: 600; cursor: pointer;">
                                            <i class="fas fa-cloud"></i> Deploy Online
                                        </button>
                                    </div>
                                </div>
                            </div>

                            <!-- Manual Setup Steps (Collapsible) -->
                            <details style="margin-bottom: 2rem;">
                                <summary style="color: var(--scikiq-light-blue); cursor: pointer; padding: 1rem; background: rgba(255, 255, 255, 0.05); border-radius: 8px; font-weight: 600;">
                                    <i class="fas fa-list-ol"></i> Or Configure Manually (Advanced)
                                </summary>
                                <div style="padding-top: 1rem;">

                            <h3 style="color: var(--scikiq-light-blue); margin-bottom: 1rem;">
                                <i class="fas fa-list-ol"></i> Manual Setup Steps
                            </h3>

                            <!-- Step 1 -->
                            <div style="background: rgba(255, 255, 255, 0.05); border-left: 4px solid var(--anthropic-orange); padding: 1.5rem; margin-bottom: 1rem; border-radius: 8px;">
                                <div style="display: flex; align-items: start; gap: 1rem;">
                                    <div style="background: var(--anthropic-orange); color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; flex-shrink: 0;">1</div>
                                    <div style="flex: 1;">
                                        <h4 style="margin: 0 0 0.5rem 0; color: white;">Install MCP SDK</h4>
                                        <p style="margin: 0 0 0.8rem 0; color: rgba(255, 255, 255, 0.8);">Install the Anthropic MCP SDK in your project:</p>
                                        <div style="background: rgba(0, 0, 0, 0.5); padding: 1rem; border-radius: 6px; font-family: 'Fira Code', monospace; position: relative;">
                                            <code style="color: #10B981;">pip install mcp httpx</code>
                                            <button onclick="copyToClipboard('pip install mcp httpx')" style="position: absolute; top: 0.5rem; right: 0.5rem; background: rgba(255, 255, 255, 0.1); border: none; color: white; padding: 0.4rem 0.8rem; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">
                                                <i class="fas fa-copy"></i>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Step 2 -->
                            <div style="background: rgba(255, 255, 255, 0.05); border-left: 4px solid var(--scikiq-light-blue); padding: 1.5rem; margin-bottom: 1rem; border-radius: 8px;">
                                <div style="display: flex; align-items: start; gap: 1rem;">
                                    <div style="background: var(--scikiq-light-blue); color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; flex-shrink: 0;">2</div>
                                    <div style="flex: 1;">
                                        <h4 style="margin: 0 0 0.5rem 0; color: white;">Configure Claude Desktop</h4>
                                        <p style="margin: 0 0 0.8rem 0; color: rgba(255, 255, 255, 0.8);">Add this to your Claude Desktop config file:</p>
                                        <div style="color: rgba(255, 255, 255, 0.7); font-size: 0.9rem; margin-bottom: 0.5rem;">
                                            <strong>Config location:</strong><br>
                                            Windows: <code style="background: rgba(0, 0, 0, 0.3); padding: 0.2rem 0.4rem; border-radius: 3px;">%APPDATA%\\\\Claude\\\\claude_desktop_config.json</code><br>
                                            Mac: <code style="background: rgba(0, 0, 0, 0.3); padding: 0.2rem 0.4rem; border-radius: 3px;">~/Library/Application Support/Claude/claude_desktop_config.json</code>
                                        </div>
                                        <div id="manualConfigExample" style="background: rgba(0, 0, 0, 0.5); padding: 1rem; border-radius: 6px; font-family: 'Fira Code', monospace; font-size: 0.85rem; position: relative; max-height: 200px; overflow-y: auto;">
<code style="color: rgba(255, 255, 255, 0.9);">{
  "mcpServers": {
    "<span id="configServerNameDisplay">scikiq-mcp-autoAPI</span>": {
      "command": "python",
      "args": ["${fullPath.replace(/\\\\/g, '\\\\\\\\')}"]
    }
  }
}</code>
                                            <button id="copyConfigBtn" onclick="copyManualConfig('${fullPath}')" style="position: absolute; top: 0.5rem; right: 0.5rem; background: rgba(255, 255, 255, 0.1); border: none; color: white; padding: 0.4rem 0.8rem; border-radius: 4px; cursor: pointer; font-size: 0.8rem;">
                                                <i class="fas fa-copy"></i>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <!-- Step 3 -->
                            <div style="background: rgba(255, 255, 255, 0.05); border-left: 4px solid var(--anthropic-purple); padding: 1.5rem; margin-bottom: 1rem; border-radius: 8px;">
                                <div style="display: flex; align-items: start; gap: 1rem;">
                                    <div style="background: var(--anthropic-purple); color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; flex-shrink: 0;">3</div>
                                    <div style="flex: 1;">
                                        <h4 style="margin: 0 0 0.5rem 0; color: white;">Restart Claude Desktop</h4>
                                        <p style="margin: 0; color: rgba(255, 255, 255, 0.8);">Completely quit and restart Claude Desktop app for the MCP server to be registered.</p>
                                    </div>
                                </div>
                            </div>

                            <!-- Step 4 -->
                            <div style="background: rgba(255, 255, 255, 0.05); border-left: 4px solid var(--success-green); padding: 1.5rem; margin-bottom: 2rem; border-radius: 8px;">
                                <div style="display: flex; align-items: start; gap: 1rem;">
                                    <div style="background: var(--success-green); color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; flex-shrink: 0;">4</div>
                                    <div style="flex: 1;">
                                        <h4 style="margin: 0 0 0.5rem 0; color: white;">Look for the Hammer Icon 🔨</h4>
                                        <p style="margin: 0; color: rgba(255, 255, 255, 0.8);">In Claude Desktop, look for the hammer/tools icon. Click it to see your ${toolCount} GLIC Insurance tools available!</p>
                                    </div>
                                </div>
                            </div>

                                </div>
                            </details>

                            <!-- One-Click Deployment Section (moved to bottom) -->
                            <div id="autoDeploySection" style="background: linear-gradient(135deg, rgba(0, 163, 224, 0.2), rgba(124, 58, 237, 0.2)); border: 2px solid var(--scikiq-light-blue); border-radius: 12px; padding: 2rem; margin-bottom: 2rem; text-align: center;">
                                <div style="font-size: 3rem; margin-bottom: 0.5rem;">🚀</div>
                                <h3 style="color: white; margin: 0 0 0.5rem 0; font-size: 1.5rem;">One-Click Deployment</h3>
                                <p style="color: rgba(255, 255, 255, 0.8); margin: 0 0 1.5rem 0; font-size: 0.95rem;">
                                    Automatically configure Claude Desktop and start using your MCP tools instantly!
                                </p>

                                <!-- MCP Server Configuration -->
                                <div style="background: rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; text-align: left;">
                                    <div style="margin-bottom: 1rem;">
                                        <label style="display: block; color: white; font-weight: 600; margin-bottom: 0.5rem;">
                                            <i class="fas fa-server"></i> MCP Server Name
                                        </label>
                                        <div style="display: flex; gap: 0.5rem; align-items: stretch;">
                                            <input type="text" id="mcpServerName" placeholder="my-api-server"
                                                style="flex: 1; padding: 0.75rem; border: 2px solid rgba(255, 255, 255, 0.3); border-radius: 6px; background: rgba(255, 255, 255, 0.1); color: white; font-size: 1rem; font-family: 'Fira Code', monospace; transition: border-color 0.3s ease;"
                                                value="scikiq-mcp-autoAPI"
                                                oninput="validateServerNameInput(this)" />
                                            <button type="button" onclick="generateSuggestedServerName()"
                                                style="padding: 0.75rem 1rem; border: 2px solid rgba(255, 255, 255, 0.3); border-radius: 6px; background: rgba(124, 58, 237, 0.2); color: white; font-size: 0.9rem; cursor: pointer; transition: all 0.3s ease; white-space: nowrap;"
                                                onmouseover="this.style.background='rgba(124, 58, 237, 0.4)'"
                                                onmouseout="this.style.background='rgba(124, 58, 237, 0.2)'">
                                                <i class="fas fa-magic"></i> Generate
                                            </button>
                                        </div>
                                        <div id="serverNameFeedback" style="margin-top: 0.5rem; font-size: 0.85rem; transition: all 0.3s ease;"></div>
                                        <small style="color: rgba(255, 255, 255, 0.7); margin-top: 0.5rem; display: block; font-size: 0.85rem;">
                                            <i class="fas fa-info-circle"></i> This name will identify your MCP server in Claude Desktop. Use lowercase letters, numbers, and hyphens only.
                                        </small>
                                    </div>
                                </div>

                                <button id="autoDeployBtn" onclick="autoDeployMCP('${fullPath}')"
                                    style="background: linear-gradient(135deg, var(--scikiq-light-blue), #7C3AED); color: white; border: none; padding: 1rem 2.5rem; border-radius: 8px; font-size: 1.1rem; font-weight: 700; cursor: pointer; box-shadow: 0 4px 15px rgba(0, 163, 224, 0.4); transition: all 0.3s ease;">
                                    <i class="fas fa-rocket"></i> Auto-Deploy to Claude Desktop
                                </button>
                                <div id="autoDeployStatus" style="margin-top: 1rem; display: none;"></div>
                            </div>

                            <!-- Action Buttons -->
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-top: 2rem;">
                                <button onclick="window.open('/glic/mcp-deployment', '_blank')" style="padding: 1rem; background: linear-gradient(135deg, var(--scikiq-light-blue), #0891B2); border: none; border-radius: 8px; color: white; font-weight: 600; cursor: pointer; font-size: 1rem;">
                                    <i class="fas fa-book-open"></i> View Full Guide
                                </button>
                                <button onclick="this.closest('[style*=fixed]').remove()" style="padding: 1rem; background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 8px; color: white; font-weight: 600; cursor: pointer; font-size: 1rem;">
                                    <i class="fas fa-check"></i> Got It!
                                </button>
                            </div>

                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHTML);

            // Load the actual code asynchronously
            loadMCPCode(filename);
        }

        async function loadMCPCode(filename) {
            try {
                const response = await fetch(`/${filename}`);
                if (response.ok) {
                    const code = await response.text();
                    const preview = document.getElementById('mcpCodePreview');
                    if (preview) {
                        // Apply basic syntax highlighting
                        preview.textContent = code;
                        applySyntaxHighlighting(preview);
                    }
                } else {
                    // If file not accessible via HTTP, show generic template
                    showGenericMCPTemplate();
                }
            } catch (error) {
                console.error('Error loading MCP code:', error);
                showGenericMCPTemplate();
            }
        }

        function showGenericMCPTemplate() {
            const preview = document.getElementById('mcpCodePreview');
            if (preview) {
                preview.innerHTML = `<span style="color: #10B981;">"""
Auto-generated MCP Server
Generated from GLIC Insurance API endpoints
"""</span>

<span style="color: #F59E0B;">from</span> mcp.server <span style="color: #F59E0B;">import</span> Server
<span style="color: #F59E0B;">from</span> mcp.server.stdio <span style="color: #F59E0B;">import</span> stdio_server
<span style="color: #F59E0B;">import</span> httpx

server = <span style="color: #3B82F6;">Server</span>(<span style="color: #10B981;">"scikiq-mcp-autoAPI"</span>)

<span style="color: #6B7280;"># Your ${window.highConfidenceAPIs?.length || 'converted'} API tools are defined here...</span>

<span style="color: #F59E0B;">@</span><span style="color: #3B82F6;">server.tool()</span>
<span style="color: #F59E0B;">async def</span> <span style="color: #3B82F6;">example_tool</span>() -> <span style="color: #F59E0B;">str</span>:
    <span style="color: #10B981;">"""Example MCP tool"""</span>
    <span style="color: #F59E0B;">async with</span> httpx.<span style="color: #3B82F6;">AsyncClient</span>() <span style="color: #F59E0B;">as</span> client:
        response = <span style="color: #F59E0B;">await</span> client.<span style="color: #3B82F6;">get</span>(<span style="color: #10B981;">"http://localhost:9321/glic/api/endpoint"</span>)
        <span style="color: #F59E0B;">return</span> response.<span style="color: #3B82F6;">json</span>()

<span style="color: #F59E0B;">async def</span> <span style="color: #3B82F6;">main</span>():
    <span style="color: #F59E0B;">async with</span> <span style="color: #3B82F6;">stdio_server</span>() <span style="color: #F59E0B;">as</span> (read_stream, write_stream):
        <span style="color: #F59E0B;">await</span> server.<span style="color: #3B82F6;">run</span>(read_stream, write_stream, server.<span style="color: #3B82F6;">create_initialization_options</span>())

<span style="color: #F59E0B;">if</span> __name__ == <span style="color: #10B981;">"__main__"</span>:
    <span style="color: #F59E0B;">import</span> asyncio
    asyncio.<span style="color: #3B82F6;">run</span>(<span style="color: #3B82F6;">main</span>())`;
            }
        }

        function applySyntaxHighlighting(element) {
            // Basic syntax highlighting for Python
            let code = element.textContent;

            // Keywords
            code = code.replace(/\b(async|await|def|class|import|from|return|if|else|elif|for|while|try|except|with|as|in)\b/g, '<span style="color: #F59E0B;">$1</span>');

            // Strings
            code = code.replace(/(["'])(?:(?=(\\?))\2.)*?\1/g, '<span style="color: #10B981;">$&</span>');

            // Comments
            code = code.replace(/(#.*)$/gm, '<span style="color: #6B7280;">$1</span>');

            // Decorators
            code = code.replace(/(@\w+)/g, '<span style="color: #F59E0B;">$1</span>');

            element.innerHTML = code;
        }

        function downloadMCPCode(filename) {
            const code = document.getElementById('mcpCodePreview').textContent;
            const blob = new Blob([code], { type: 'text/x-python' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }

        function generateServerNameSuggestion() {
            const apiNameInput = document.getElementById('apiName');
            const serverNameInput = document.getElementById('mcpServerName');

            if (apiNameInput && apiNameInput.value && serverNameInput) {
                // Convert API name to valid server name format
                let suggestion = apiNameInput.value.toLowerCase()
                    .replace(/[^a-z0-9\s-]/g, '') // Remove special characters except spaces and hyphens
                    .replace(/\s+/g, '-') // Replace spaces with hyphens
                    .replace(/-+/g, '-') // Replace multiple hyphens with single hyphen
                    .replace(/^-+|-+$/g, ''); // Remove leading/trailing hyphens

                if (suggestion.length > 0) {
                    serverNameInput.value = suggestion;
                    validateServerNameInput(serverNameInput);
                }
            }
        }

        function generateSuggestedServerName() {
            const serverNameInput = document.getElementById('mcpServerName');
            const apiNameInput = document.getElementById('apiName');

            let suggestions = [];

            // Try to generate from API name first
            if (apiNameInput && apiNameInput.value) {
                let suggestion = apiNameInput.value.toLowerCase()
                    .replace(/[^a-z0-9\s-]/g, '')
                    .replace(/\s+/g, '-')
                    .replace(/-+/g, '-')
                    .replace(/^-+|-+$/g, '');
                if (suggestion) suggestions.push(suggestion);
            }

            // Add some generic suggestions
            suggestions.push(
                'my-api-server',
                'api-mcp-server',
                'custom-api-tools',
                'api-connector'
            );

            // Use the first valid suggestion
            for (let suggestion of suggestions) {
                const validation = validateServerName(suggestion);
                if (validation.valid) {
                    serverNameInput.value = suggestion;
                    validateServerNameInput(serverNameInput);
                    break;
                }
            }
        }

        function validateServerName(name) {
            // Check format
            if (!/^[a-zA-Z0-9_-]+$/.test(name)) {
                return { valid: false, message: 'Server name can only contain letters, numbers, hyphens, and underscores' };
            }

            // Check length
            if (name.length < 2) {
                return { valid: false, message: 'Server name must be at least 2 characters long' };
            }

            if (name.length > 50) {
                return { valid: false, message: 'Server name must be 50 characters or less' };
            }

            // Check that it doesn't start with hyphen
            if (name.startsWith('-') || name.startsWith('_')) {
                return { valid: false, message: 'Server name cannot start with hyphen or underscore' };
            }

            return { valid: true };
        }

        function validateServerNameInput(input) {
            const feedback = document.getElementById('serverNameFeedback');
            const name = input.value.trim();

            // Update manual configuration display
            updateManualConfigDisplay(name);

            if (!name) {
                feedback.innerHTML = '';
                input.style.borderColor = 'rgba(255, 255, 255, 0.3)';
                return;
            }

            const validation = validateServerName(name);

            if (validation.valid) {
                feedback.innerHTML = '<i class="fas fa-check-circle" style="color: #10B981;"></i> <span style="color: #10B981;">Valid server name</span>';
                input.style.borderColor = '#10B981';
            } else {
                feedback.innerHTML = `<i class="fas fa-exclamation-triangle" style="color: #EF4444;"></i> <span style="color: #EF4444;">${validation.message}</span>`;
                input.style.borderColor = '#EF4444';
            }
        }

        function updateManualConfigDisplay(serverName) {
            const displayElement = document.getElementById('configServerNameDisplay');
            if (displayElement && serverName) {
                displayElement.textContent = serverName;
            }
        }

        function copyManualConfig(serverPath) {
            const serverNameInput = document.getElementById('mcpServerName');
            const serverName = serverNameInput ? serverNameInput.value.trim() : 'scikiq-mcp-autoAPI';

            const config = {
                "mcpServers": {}
            };
            config.mcpServers[serverName] = {
                "command": "python",
                "args": [serverPath.replace(/\\\\/g, '\\\\')]
            };

            const configText = JSON.stringify(config, null, 2);
            copyToClipboard(configText);
        }

        async function autoDeployMCP(serverPath) {
            const btn = document.getElementById('autoDeployBtn');
            const statusDiv = document.getElementById('autoDeployStatus');
            const serverNameInput = document.getElementById('mcpServerName');

            // Get server name from input field and validate
            let serverName = serverNameInput.value.trim();
            if (!serverName) {
                alert('Please enter a server name');
                return;
            }

            // Validate server name
            const validation = validateServerName(serverName);
            if (!validation.valid) {
                alert(validation.message);
                return;
            }

            // Disable button and show loading
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Deploying...';
            statusDiv.style.display = 'block';
            statusDiv.innerHTML = `<div style="color: var(--scikiq-light-blue);"><i class="fas fa-spinner fa-spin"></i> Configuring Claude Desktop with server name: <strong>${serverName}</strong>...</div>`;

            try {
                // Include yaml_path if available from last conversion
                const yamlPath = window.lastGeneratedYamlPath || null;

                const response = await fetch('/api/auto-deploy-mcp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        server_path: serverPath,  // Send path as-is, let backend handle normalization
                        yaml_path: yamlPath,      // Include YAML file path so config includes it as arg
                        server_name: serverName,
                        auto_restart: true
                    })
                });

                const result = await response.json();

                if (result.success) {
                    // Generate diagnostics accordion HTML
                    const diagnosticsHtml = result.diagnostics ? generateDiagnosticsAccordion(result.diagnostics, result.attempts || 1) : '';

                    // Check log status for errors
                    const hasLogErrors = result.log_status && result.log_status.has_errors;

                    if (hasLogErrors) {
                        // Show warning - deployed but has errors
                        btn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Deployed with Issues';
                        btn.style.background = 'linear-gradient(135deg, #FBBF24, #F59E0B)';

                        statusDiv.innerHTML = `
                            <div style="background: rgba(251, 191, 36, 0.2); border: 2px solid #FBBF24; border-radius: 8px; padding: 1.5rem; text-align: left;">
                                <h4 style="color: #FBBF24; margin: 0 0 1rem 0;">
                                    <i class="fas fa-exclamation-triangle"></i> Deployment Complete but Server Has Errors
                                </h4>
                                <div style="color: rgba(255, 255, 255, 0.9); line-height: 1.8;">
                                    <div style="margin-bottom: 0.5rem;"><i class="fas fa-check" style="color: var(--success-green);"></i> Config file updated: <code style="background: rgba(0,0,0,0.3); padding: 0.2rem 0.5rem; border-radius: 4px;">${result.config_path}</code></div>
                                    <div style="margin-bottom: 0.5rem;"><i class="fas fa-check" style="color: var(--success-green);"></i> MCP server registered as: <strong>${result.server_name}</strong></div>
                                    <div style="margin-bottom: 1rem;"><i class="fas fa-times" style="color: #EF4444;"></i> Server failed to start - found errors in logs</div>

                                    <div style="background: rgba(239, 68, 68, 0.2); border-left: 4px solid #EF4444; padding: 1rem; border-radius: 6px; margin: 1rem 0;">
                                        <h5 style="color: #EF4444; margin: 0 0 0.75rem 0;">
                                            <i class="fas fa-bug"></i> Error Details
                                        </h5>
                                        <pre style="background: rgba(0,0,0,0.3); padding: 0.75rem; border-radius: 4px; overflow-x: auto; font-size: 0.85rem; margin: 0;">${result.log_status.errors ? result.log_status.errors.slice(0, 3).join('\n') : 'Check Claude Desktop logs for details'}</pre>
                                    </div>

                                    <div style="background: rgba(0, 163, 224, 0.1); border-left: 4px solid var(--scikiq-light-blue); padding: 1rem; border-radius: 6px; margin-top: 1rem;">
                                        <h5 style="color: var(--scikiq-light-blue); margin: 0 0 0.75rem 0;">
                                            <i class="fas fa-sync-alt"></i> Solution: Regenerate MCP Server
                                        </h5>
                                        <p style="margin: 0 0 0.5rem 0; font-size: 0.9rem;">Your MCP server uses outdated syntax. Please:</p>
                                        <ol style="margin: 0.5rem 0 0 1.5rem; padding: 0; font-size: 0.9rem;">
                                            <li style="margin-bottom: 0.5rem;">Click <strong>"Convert Top APIs"</strong> button above to regenerate the MCP server</li>
                                            <li style="margin-bottom: 0.5rem;">Wait for the new server file to be created</li>
                                            <li style="margin-bottom: 0.5rem;">Click <strong>"Auto-Deploy"</strong> again</li>
                                            <li>Restart Claude Desktop manually if needed</li>
                                        </ol>
                                    </div>

                                    <button onclick="autoDeployMCP('${result.server_path}')"
                                            style="background: linear-gradient(135deg, var(--scikiq-light-blue), #7C3AED);
                                                   color: white;
                                                   padding: 0.75rem 1.5rem;
                                                   border: none;
                                                   border-radius: 6px;
                                                   cursor: pointer;
                                                   font-weight: 600;
                                                   margin-top: 1rem;
                                                   width: 100%;
                                                   font-size: 1rem;
                                                   transition: all 0.3s ease;
                                                   box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);"
                                            onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 12px rgba(0, 0, 0, 0.15)';"
                                            onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px rgba(0, 0, 0, 0.1)';">
                                        <i class="fas fa-redo"></i> Retry Deployment
                                    </button>
                                </div>

                                ${diagnosticsHtml}
                                </div>
                            </div>
                        `;
                    } else {
                        // Show success with test samples
                        btn.innerHTML = '<i class="fas fa-check-circle"></i> Deployed Successfully!';
                        btn.style.background = 'linear-gradient(135deg, var(--success-green), #059669)';

                        statusDiv.innerHTML = `
                            <div style="background: rgba(16, 185, 129, 0.2); border: 2px solid var(--success-green); border-radius: 8px; padding: 1.5rem; text-align: left;">
                                <h4 style="color: var(--success-green); margin: 0 0 1rem 0;">
                                    <i class="fas fa-check-circle"></i> Deployment Complete!
                                </h4>
                                <div style="color: rgba(255, 255, 255, 0.9); line-height: 1.8;">
                                    <div style="margin-bottom: 0.5rem;"><i class="fas fa-check" style="color: var(--success-green);"></i> Config file updated: <code style="background: rgba(0,0,0,0.3); padding: 0.2rem 0.5rem; border-radius: 4px;">${result.config_path}</code></div>
                                    <div style="margin-bottom: 0.5rem;"><i class="fas fa-check" style="color: var(--success-green);"></i> MCP server registered as: <strong>${result.server_name}</strong></div>
                                    <div style="margin-bottom: 0.5rem;"><i class="fas fa-${result.restart_success ? 'check' : 'exclamation-triangle'}" style="color: ${result.restart_success ? 'var(--success-green)' : '#FBBF24'};"></i> Claude Desktop ${result.restart_success ? 'restarted successfully' : 'restart attempted (may need manual restart)'}</div>
                                    <div style="margin-bottom: 1rem;"><i class="fas fa-check" style="color: var(--success-green);"></i> Server validation: ${result.log_status && result.log_status.checked ? 'No errors found in logs' : 'Logs check skipped'}</div>

                                <div style="background: rgba(0, 163, 224, 0.1); border-left: 4px solid var(--scikiq-light-blue); padding: 1rem; border-radius: 6px; margin-top: 1rem;">
                                    <h5 style="color: var(--scikiq-light-blue); margin: 0 0 0.75rem 0;">
                                        <i class="fas fa-comment-dots"></i> Test Your Tools in Claude Desktop
                                    </h5>
                                    <div style="font-size: 0.9rem; color: rgba(255, 255, 255, 0.8);">
                                        <p style="margin: 0 0 0.5rem 0;">Open Claude Desktop and try these queries:</p>
                                        <ul style="margin: 0.5rem 0; padding-left: 1.5rem;">
                                            <li>"Create a customer named John Smith with email john@example.com"</li>
                                            <li>"Show me all active policies for customer ID 12345"</li>
                                            <li>"Generate an auto insurance quote for a 2023 Toyota Camry"</li>
                                            <li>"Find all in-network hospitals in zip code 10001"</li>
                                        </ul>
                                        <p style="margin: 0.75rem 0 0 0; font-style: italic;">Look for the 🔨 hammer icon in Claude Desktop to see your tools!</p>
                                    </div>
                                </div>

                                ${diagnosticsHtml}
                                </div>
                            </div>
                        `;
                    }
                } else {
                    throw new Error(result.error || 'Deployment failed');
                }

            } catch (error) {
                console.error('Auto-deploy error:', error);
                btn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Deployment Failed';
                btn.style.background = 'linear-gradient(135deg, #EF4444, #B91C1C)';
                btn.disabled = false;

                const isValidationError = error.message && error.message.includes('validation failed');

                // Try to get diagnostics from caught error
                let diagnosticsHtml = '';
                if (error.response) {
                    try {
                        const errorData = await error.response.json();
                        if (errorData.diagnostics) {
                            diagnosticsHtml = generateDiagnosticsAccordion(errorData.diagnostics, errorData.attempts || 0);
                        }
                    } catch (e) {
                        console.error('Could not parse error diagnostics', e);
                    }
                }

                statusDiv.innerHTML = `
                    <div style="background: rgba(239, 68, 68, 0.2); border: 2px solid #EF4444; border-radius: 8px; padding: 1.5rem; text-align: left;">
                        <h4 style="color: #EF4444; margin: 0 0 1rem 0;">
                            <i class="fas fa-exclamation-triangle"></i> Deployment Failed
                        </h4>
                        <p style="color: rgba(255, 255, 255, 0.9); margin: 0 0 1rem 0;">
                            <strong>Error:</strong> ${error.message}
                        </p>
                        ${isValidationError ? `
                            <div style="background: rgba(0, 163, 224, 0.1); border-left: 4px solid var(--scikiq-light-blue); padding: 1rem; border-radius: 6px;">
                                <h5 style="color: var(--scikiq-light-blue); margin: 0 0 0.75rem 0;">
                                    <i class="fas fa-sync-alt"></i> Solution
                                </h5>
                                <p style="margin: 0; font-size: 0.9rem;">Please regenerate the MCP server by clicking <strong>"Convert Top APIs"</strong> button above, then try deploying again.</p>
                            </div>
                        ` : `
                            <p style="color: rgba(255, 255, 255, 0.8); margin: 0; font-size: 0.9rem;">
                                Please use the manual setup steps below or check the console for details.
                            </p>
                        `}
                        ${diagnosticsHtml}
                    </div>
                `;
            }
        }

        function generateDiagnosticsAccordion(diagnostics, attempts) {
            if (!diagnostics || diagnostics.length === 0) return '';

            const levelColors = {
                'success': '#10B981',
                'info': '#3B82F6',
                'warning': '#FBBF24',
                'error': '#EF4444'
            };

            const levelIcons = {
                'success': 'fa-check-circle',
                'info': 'fa-info-circle',
                'warning': 'fa-exclamation-triangle',
                'error': 'fa-times-circle'
            };

            const diagnosticsRows = diagnostics.map(log => {
                const color = levelColors[log.level] || '#6B7280';
                const icon = levelIcons[log.level] || 'fa-circle';
                const time = new Date(log.timestamp).toLocaleTimeString();

                return `
                    <div style="display: flex; gap: 0.75rem; padding: 0.5rem 0; border-bottom: 1px solid rgba(255, 255, 255, 0.1);">
                        <div style="min-width: 60px; color: rgba(255, 255, 255, 0.6); font-size: 0.8rem;">${time}</div>
                        <div style="min-width: 20px;">
                            <i class="fas ${icon}" style="color: ${color};"></i>
                        </div>
                        <div style="flex: 1; color: rgba(255, 255, 255, 0.9); font-size: 0.9rem;">${log.message}</div>
                    </div>
                `;
            }).join('');

            return `
                <details style="margin-top: 1rem; background: rgba(0, 0, 0, 0.3); border-radius: 6px; overflow: hidden;">
                    <summary style="padding: 1rem; cursor: pointer; user-select: none; background: rgba(0, 0, 0, 0.2); font-weight: 600; color: rgba(255, 255, 255, 0.95);">
                        <i class="fas fa-list-ul"></i> Deployment Diagnostics (${attempts} attempt${attempts !== 1 ? 's' : ''}, ${diagnostics.length} logs)
                    </summary>
                    <div style="padding: 1rem; max-height: 400px; overflow-y: auto;">
                        ${diagnosticsRows}
                    </div>
                </details>
            `;
        }

        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                // Show brief success feedback
                const btn = event.target.closest('button');
                const originalHTML = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
                btn.style.background = 'var(--success-green)';
                setTimeout(() => {
                    btn.innerHTML = originalHTML;
                    btn.style.background = '';
                }, 2000);
            });
        }

        // ==================== CLIENT INSTALLATION FUNCTIONS ====================

        function installSwaggerMCP() {
            const swaggerUrl = document.getElementById('swaggerUrl').value;
            const baseUrl = document.getElementById('baseUrl').value;
            const authType = document.getElementById('authType').value;
            const authToken = document.getElementById('authToken').value;
            const authUser = document.getElementById('authUser').value;
            const authPass = document.getElementById('authPass').value;
            const apiName = document.getElementById('apiName').value;

            if (!swaggerUrl) {
                alert('Please provide a Swagger/OpenAPI URL');
                return;
            }

            const serverConfig = {
                swagger_url: swaggerUrl,
                base_url: baseUrl,
                auth_type: authType,
                auth_token: authToken,
                auth_user: authUser,
                auth_pass: authPass,
                api_name: apiName
            };

            showInstallationModal('swagger', 'Swagger API MCP Server', serverConfig);
        }

        function installCodebaseMCP() {
            const projectPath = document.getElementById('projectPath').value;
            const sourceFile = document.getElementById('sourceFile').value;
            const apiServerUrl = document.getElementById('apiServerUrl').value;

            if (!projectPath) {
                alert('Please provide a project path');
                return;
            }

            const serverConfig = {
                project_path: projectPath,
                source_file: sourceFile,
                api_server_url: apiServerUrl
            };

            showInstallationModal('codebase', 'Codebase MCP Server', serverConfig);
        }

        function installDatabaseMCP() {
            const serverName = document.getElementById('dbServerName').value;
            const serverPath = document.getElementById('dbServerPath').value;

            if (!serverName || !serverPath) {
                alert('Please provide server name and path');
                return;
            }

            // Collect database connections
            const connections = [];
            const connectionElements = document.querySelectorAll('.database-connection');

            for (let connectionEl of connectionElements) {
                const connection = {};
                const inputs = connectionEl.querySelectorAll('input, select');
                for (let input of inputs) {
                    if (input.name && input.value) {
                        connection[input.name] = input.value;
                    }
                }
                if (connection.connection_name && connection.db_type) {
                    connections.push(connection);
                }
            }

            if (connections.length === 0) {
                alert('Please add at least one database connection');
                return;
            }

            const serverConfig = {
                server_name: serverName,
                server_path: serverPath,
                connections: connections
            };

            showInstallationModal('database', 'Database MCP Server', serverConfig);
        }

        function installLocallyAfterAnalysis() {
            if (!window.highConfidenceAPIs || window.highConfidenceAPIs.length === 0) {
                alert('No analyzed APIs found. Please run bulk analysis first.');
                return;
            }

            // Debug logging
            console.log('installLocallyAfterAnalysis called');
            console.log('projectSourceType:', typeof projectSourceType !== 'undefined' ? projectSourceType : 'undefined');
            console.log('selectedSwaggerConfig:', typeof selectedSwaggerConfig !== 'undefined' ? selectedSwaggerConfig : 'undefined');
            console.log('selectedProjectConfig:', typeof selectedProjectConfig !== 'undefined' ? selectedProjectConfig : 'undefined');

            // Close the bulk analysis modal first
            const bulkAnalysisModal = document.querySelector('[style*="position: fixed"][style*="z-index: 10000"]');
            if (bulkAnalysisModal) {
                bulkAnalysisModal.remove();
            }

            // Determine server type and config based on project source
            let serverType, serverDisplayName, serverConfig;

            // Check if projectSourceType is defined and determine type
            const sourceType = (typeof projectSourceType !== 'undefined') ? projectSourceType : 'codebase';

            if (sourceType === 'swagger') {
                serverType = 'swagger';
                serverDisplayName = 'Analyzed Swagger MCP Server';

                // Get Swagger configuration with fallbacks
                const baseUrlInput = document.getElementById('baseUrl');
                const apiNameInput = document.getElementById('apiName');

                serverConfig = {
                    analyzed_apis: window.highConfidenceAPIs,
                    api_count: window.highConfidenceAPIs.length,
                    swagger_url: (typeof selectedSwaggerConfig !== 'undefined' && selectedSwaggerConfig.swagger_url) || '',
                    base_url: baseUrlInput ? baseUrlInput.value : ((typeof selectedSwaggerConfig !== 'undefined' && selectedSwaggerConfig.api_base_url) || ''),
                    api_name: apiNameInput ? apiNameInput.value : 'Analyzed API Service'
                };
            } else {
                serverType = 'codebase';
                serverDisplayName = 'Analyzed Codebase MCP Server';

                serverConfig = {
                    analyzed_apis: window.highConfidenceAPIs,
                    api_count: window.highConfidenceAPIs.length,
                    project_path: (typeof selectedProjectConfig !== 'undefined' && selectedProjectConfig.project_path) || '',
                    source_file: (typeof selectedProjectConfig !== 'undefined' && selectedProjectConfig.source_file) || '',
                    api_server_url: (typeof selectedProjectConfig !== 'undefined' && selectedProjectConfig.api_base_url) || 'http://localhost:9321'
                };
            }

            console.log('Final serverConfig:', serverConfig);
            showInstallationModal(serverType, serverDisplayName, serverConfig);
        }

        function showInstallationModal(serverType, serverDisplayName, serverConfig) {
            // Store the server config globally for the installer generation
            window.currentServerConfig = serverConfig;

            const modalHTML = `
                <div class="input-modal" id="installationModal">
                    <div class="input-modal-content" style="max-width: 700px; position: relative;">
                        <button onclick="document.getElementById('installationModal').remove()" style="position: absolute; top: 1rem; right: 1rem; background: rgba(255, 255, 255, 0.2); border: none; color: white; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; transition: all 0.3s ease; z-index: 10;" onmouseover="this.style.background='rgba(255, 255, 255, 0.3)'" onmouseout="this.style.background='rgba(255, 255, 255, 0.2)'">
                            <i class="fas fa-times"></i>
                        </button>
                        <h3><i class="fas fa-cloud-download-alt"></i> Install ${serverDisplayName} Locally</h3>
                        <p style="color: rgba(255, 255, 255, 0.7); margin-bottom: 1.5rem;">
                            This will generate an installer script that you can run on your machine to automatically set up the MCP server with a virtual environment.
                        </p>

                        <div class="input-group">
                            <label>Installation Directory</label>
                            <div style="display: flex; gap: 0.5rem;">
                                <input type="text" id="installationPath" placeholder="C:/MCP_Servers or /home/user/mcp_servers" value="${getDefaultInstallPath()}" style="flex: 1;" />
                                <button type="button" onclick="browseInstallationPath()" style="background: var(--scikiq-light-blue); border: none; color: white; padding: 0.75rem 1rem; border-radius: 6px; cursor: pointer;">
                                    <i class="fas fa-folder-open"></i> Browse
                                </button>
                            </div>
                            <small style="color: rgba(255, 255, 255, 0.5); margin-top: 0.5rem; display: block;">
                                Directory where the MCP server will be installed
                            </small>
                        </div>

                        <div class="input-group">
                            <label>Server Name</label>
                            <input type="text" id="clientServerName" placeholder="my_mcp_server" value="${generateServerName(serverType)}" />
                            <small style="color: rgba(255, 255, 255, 0.5); margin-top: 0.5rem; display: block;">
                                Unique name for this MCP server
                            </small>
                        </div>

                        <!-- Installation Features -->
                        <div style="background: rgba(16, 185, 129, 0.1); border-left: 4px solid var(--success-green); padding: 0.6rem 1rem; margin: 1rem 0 0.5rem 0; border-radius: 8px;">
                            <h4 style="margin: 0 0 0.8rem; color: var(--success-green); font-size: 0.95rem;">
                                <i class="fas fa-check-circle"></i> What will be installed:
                            </h4>
                            <ul style="margin: 0; padding-left: 1.5rem; color: rgba(255, 255, 255, 0.8);">
                                <li>Python virtual environment with MCP dependencies</li>
                                <li>MCP server code and configuration files</li>
                                <li>Automatic Claude Desktop configuration</li>
                                <li>Convenience run scripts</li>
                            </ul>
                        </div>

                        <!-- Requirements -->
                        <div style="background: rgba(59, 130, 246, 0.1); border-left: 4px solid #3B82F6; padding: 0.6rem 1rem; margin: 1rem 0 0.5rem 0; border-radius: 8px;">
                            <h4 style="margin: 0 0 0.8rem; color: #3B82F6; font-size: 0.95rem;">
                                <i class="fas fa-info-circle"></i> Requirements:
                            </h4>
                            <ul style="margin: 0; padding-left: 1.5rem; color: rgba(255, 255, 255, 0.8);">
                                <li>Python 3.8 or higher</li>
                                <li>Internet connection for package downloads</li>
                                <li>Write permissions to installation directory</li>
                                <li>Claude Desktop (for automatic configuration)</li>
                            </ul>
                        </div>

                        <div class="input-buttons">
                            <button class="btn-secondary-custom" onclick="closeInstallationModal()">
                                <i class="fas fa-times"></i> Cancel
                            </button>
                            <button class="btn-success-custom" onclick="generateInstaller('${serverType}')">
                                <i class="fas fa-download"></i> Download Installer
                            </button>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHTML);

            // Store server config for later use
            window.currentServerConfig = serverConfig;
        }

        function closeInstallationModal() {
            const modal = document.getElementById('installationModal');
            if (modal) modal.remove();
        }

        function getDefaultInstallPath() {
            // Detect OS and provide appropriate default path
            const isWindows = navigator.platform.indexOf('Win') !== -1;
            if (isWindows) {
                return 'C:\\MCP_Servers';
            } else {
                return '/home/user/mcp_servers';
            }
        }

        function generateServerName(serverType) {
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
            return `${serverType}_mcp_${timestamp}`;
        }

        function browseInstallationPath() {
            // Note: Web browsers cannot directly browse local directories
            // This would need to be implemented with a file input or server-side helper
            alert('Note: Please manually enter the installation path. Web browsers cannot directly browse local directories for security reasons.');
        }

        async function generateInstaller(serverType) {
            try {
                const installationPath = document.getElementById('installationPath').value;
                const serverName = document.getElementById('clientServerName').value;

                if (!installationPath || !serverName) {
                    alert('Please provide installation path and server name');
                    return;
                }

                // Debug logging
                console.log('generateInstaller called with:', {
                    serverType,
                    installationPath,
                    serverName,
                    currentServerConfig: window.currentServerConfig
                });

                if (!window.currentServerConfig) {
                    throw new Error('Server configuration not found. Please try again.');
                }

                // Show loading
                const button = event.target;
                const originalText = button.innerHTML;
                button.innerHTML = '<div class="loading-spinner"></div> Generating...';
                button.disabled = true;

                // Generate installer
                const response = await fetch('/api/generate-installer', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        installation_path: installationPath,
                        server_name: serverName,
                        server_type: serverType,
                        server_config: window.currentServerConfig
                    })
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    console.error('Server response error:', response.status, errorText);
                    throw new Error(`Server error (${response.status}): ${errorText}`);
                }

                const result = await response.json();

                if (result.success) {
                    // Close modal
                    closeInstallationModal();

                    // Show download success modal
                    showInstallerDownloadModal(result);
                } else {
                    throw new Error(result.error || 'Failed to generate installer');
                }

            } catch (error) {
                console.error('Error generating installer:', error);
                alert('Error: ' + error.message);
            } finally {
                // Reset button
                const button = event.target;
                if (button) {
                    button.innerHTML = originalText;
                    button.disabled = false;
                }
            }
        }

        function showInstallerDownloadModal(result) {
            const modalHTML = `
                <div class="input-modal" id="downloadModal">
                    <div class="input-modal-content" style="max-width: 800px; position: relative;">
                        <button onclick="document.getElementById('downloadModal').remove()" style="position: absolute; top: 1rem; right: 1rem; background: rgba(255, 255, 255, 0.2); border: none; color: white; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; transition: all 0.3s ease; z-index: 10;" onmouseover="this.style.background='rgba(255, 255, 255, 0.3)'" onmouseout="this.style.background='rgba(255, 255, 255, 0.2)'">
                            <i class="fas fa-times"></i>
                        </button>
                        <h3><i class="fas fa-check-circle" style="color: var(--success-green);"></i> Installer Generated Successfully!</h3>
                        
                        <div style="background: rgba(16, 185, 129, 0.1); border: 2px solid var(--success-green); border-radius: 12px; padding: 1.5rem; margin: 1.5rem 0;">
                            <div style="text-align: center; margin-bottom: 1rem;">
                                <button onclick="downloadInstaller('${result.installer_filename}')" 
                                        style="background: linear-gradient(135deg, var(--success-green), #059669); color: white; border: none; padding: 1rem 2rem; border-radius: 10px; font-size: 1.1rem; font-weight: 600; cursor: pointer; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);">
                                    <i class="fas fa-download"></i> Download Installer (${result.installer_filename})
                                </button>
                            </div>
                            <p style="text-align: center; color: rgba(255, 255, 255, 0.7); margin: 0;">
                                Click to download the installer script to your computer
                            </p>
                        </div>

                        <div style="background: rgba(255, 255, 255, 0.05); border-radius: 8px; padding: 1.5rem; margin: 1.5rem 0;">
                            <h4 style="margin: 0 0 1rem; color: var(--scikiq-light-blue);">
                                <i class="fas fa-list-ol"></i> Installation Steps:
                            </h4>
                            <ol style="margin: 0; padding-left: 1.5rem; color: rgba(255, 255, 255, 0.8); line-height: 1.6;">
                                ${result.instructions.steps.map(step => `<li>${step}</li>`).join('')}
                            </ol>
                        </div>

                        <div style="background: rgba(251, 191, 36, 0.1); border-left: 4px solid #F59E0B; padding: 0.6rem 1rem; margin: 1rem 0 0.5rem 0; border-radius: 8px;">
                            <h4 style="margin: 0 0 0.8rem; color: #F59E0B; font-size: 0.95rem;">
                                <i class="fas fa-exclamation-triangle"></i> Troubleshooting:
                            </h4>
                            <ul style="margin: 0; padding-left: 1.5rem; color: rgba(255, 255, 255, 0.8);">
                                ${result.instructions.troubleshooting.map(tip => `<li>${tip}</li>`).join('')}
                            </ul>
                        </div>

                        <div class="input-buttons">
                            <button class="btn-primary-custom" onclick="closeDownloadModal()">
                                <i class="fas fa-check"></i> Got It!
                            </button>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHTML);
        }

        function downloadInstaller(filename) {
            window.open(`/download-installer/${filename}`, '_blank');
        }


        function closeDownloadModal() {
            const modal = document.getElementById('downloadModal');
            if (modal) modal.remove();
        }

        // Online Publishing Functions
        function showPublishOnlineModal() {
            const modalHTML = `
                <div class="input-modal" id="publishOnlineModal">
                    <div class="input-modal-content" style="max-width: 800px; max-height: 90vh; overflow-y: auto; position: relative;">
                        <button onclick="document.getElementById('publishOnlineModal').remove()" style="position: absolute; top: 1rem; right: 1rem; background: rgba(255, 255, 255, 0.2); border: none; color: white; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; transition: all 0.3s ease; z-index: 10;" onmouseover="this.style.background='rgba(255, 255, 255, 0.3)'" onmouseout="this.style.background='rgba(255, 255, 255, 0.2)'">
                            <i class="fas fa-times"></i>
                        </button>
                        <h3><i class="fas fa-cloud-upload-alt"></i> Publish MCP Server Online</h3>
                        <p style="color: rgba(255, 255, 255, 0.7); margin-bottom: 1.5rem;">
                            Deploy your MCP server to the cloud or remote machine
                        </p>

                        <!-- Deployment Type Tabs -->
                        <div style="display: flex; gap: 0.5rem; margin-bottom: 1.5rem; border-bottom: 2px solid rgba(255, 255, 255, 0.1);">
                            <button onclick="switchDeploymentTab('aws')" class="deployment-tab active" data-tab="aws" style="flex: 1; padding: 0.8rem; background: transparent; border: none; border-bottom: 3px solid transparent; color: rgba(255, 255, 255, 0.6); cursor: pointer; transition: all 0.3s;">
                                <i class="fab fa-aws"></i> AWS EC2
                            </button>
                            <button onclick="switchDeploymentTab('azure')" class="deployment-tab" data-tab="azure" style="flex: 1; padding: 0.8rem; background: transparent; border: none; border-bottom: 3px solid transparent; color: rgba(255, 255, 255, 0.6); cursor: pointer; transition: all 0.3s;">
                                <i class="fab fa-microsoft"></i> Azure VM
                            </button>
                            <button onclick="switchDeploymentTab('remote')" class="deployment-tab" data-tab="remote" style="flex: 1; padding: 0.8rem; background: transparent; border: none; border-bottom: 3px solid transparent; color: rgba(255, 255, 255, 0.6); cursor: pointer; transition: all 0.3s;">
                                <i class="fas fa-server"></i> Remote SSH
                            </button>
                        </div>

                        <!-- AWS Tab -->
                        <div id="aws-deploy-tab" class="deployment-tab-content" style="display: block;">
                            <div class="input-group">
                                <label>AWS Access Key <span style="color: var(--anthropic-orange);">*</span></label>
                                <input type="text" id="awsAccessKey" placeholder="AKIA..." />
                            </div>
                            <div class="input-group">
                                <label>AWS Secret Key <span style="color: var(--anthropic-orange);">*</span></label>
                                <input type="password" id="awsSecretKey" placeholder="Secret access key" />
                            </div>
                            <div class="input-group">
                                <label>AWS Region <span style="color: var(--anthropic-orange);">*</span></label>
                                <select id="awsRegion" style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 8px; padding: 0.8rem; color: white; width: 100%;">
                                    <option value="us-east-1">US East (N. Virginia) - us-east-1</option>
                                    <option value="us-east-2">US East (Ohio) - us-east-2</option>
                                    <option value="us-west-1">US West (N. California) - us-west-1</option>
                                    <option value="us-west-2">US West (Oregon) - us-west-2</option>
                                    <option value="eu-west-1">EU (Ireland) - eu-west-1</option>
                                    <option value="eu-west-2">EU (London) - eu-west-2</option>
                                    <option value="eu-west-3">EU (Paris) - eu-west-3</option>
                                    <option value="eu-central-1">EU (Frankfurt) - eu-central-1</option>
                                    <option value="ap-southeast-1">Asia Pacific (Singapore) - ap-southeast-1</option>
                                    <option value="ap-southeast-2">Asia Pacific (Sydney) - ap-southeast-2</option>
                                    <option value="ap-south-1" selected>Asia Pacific (Mumbai) - ap-south-1</option>
                                    <option value="ap-northeast-1">Asia Pacific (Tokyo) - ap-northeast-1</option>
                                    <option value="ap-northeast-2">Asia Pacific (Seoul) - ap-northeast-2</option>
                                    <option value="ca-central-1">Canada (Central) - ca-central-1</option>
                                    <option value="sa-east-1">South America (São Paulo) - sa-east-1</option>
                                </select>
                            </div>
                            <div class="input-group">
                                <label>Instance Type <span style="color: var(--anthropic-orange);">*</span></label>
                                <select id="awsInstanceType" style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 8px; padding: 0.8rem; color: white; width: 100%;">
                                    <option value="t2.micro" selected>t2.micro (1 vCPU, 1GB RAM) - Free tier eligible</option>
                                    <option value="t2.small">t2.small (1 vCPU, 2GB RAM)</option>
                                    <option value="t2.medium">t2.medium (2 vCPU, 4GB RAM)</option>
                                    <option value="t2.large">t2.large (2 vCPU, 8GB RAM)</option>
                                    <option value="t3.micro">t3.micro (2 vCPU, 1GB RAM) - Burstable</option>
                                    <option value="t3.small">t3.small (2 vCPU, 2GB RAM) - Burstable</option>
                                    <option value="t3.medium">t3.medium (2 vCPU, 4GB RAM) - Burstable</option>
                                    <option value="t3.large">t3.large (2 vCPU, 8GB RAM) - Burstable</option>
                                    <option value="m5.large">m5.large (2 vCPU, 8GB RAM) - General purpose</option>
                                    <option value="m5.xlarge">m5.xlarge (4 vCPU, 16GB RAM) - General purpose</option>
                                    <option value="c5.large">c5.large (2 vCPU, 4GB RAM) - Compute optimized</option>
                                    <option value="c5.xlarge">c5.xlarge (4 vCPU, 8GB RAM) - Compute optimized</option>
                                </select>
                            </div>
                            <div class="input-group">
                                <label>Domain Name (Optional)</label>
                                <input type="text" id="awsDomain" placeholder="api.yourdomain.com" />
                                <small style="color: rgba(255, 255, 255, 0.5);">Leave empty to use public IP. Format: subdomain.domain.com (no http:// or https://)</small>
                            </div>
                            <div class="input-group" style="display: flex; align-items: center; gap: 0.8rem; margin-top: 1rem;">
                                <input type="checkbox" id="awsAutoDownloadLogs" style="width: 20px; height: 20px; cursor: pointer; accent-color: var(--anthropic-orange);" />
                                <label for="awsAutoDownloadLogs" style="cursor: pointer; margin: 0;">
                                    <i class="fas fa-file-download"></i> Auto-download logs after deployment
                                </label>
                                <small style="color: rgba(255, 255, 255, 0.5); display: block; margin-left: 28px;">(Wait for setup completion and fetch EC2 console logs)</small>
                            </div>
                        </div>

                        <!-- Azure Tab -->
                        <div id="azure-deploy-tab" class="deployment-tab-content" style="display: none;">
                            <div class="input-group">
                                <label>Subscription ID <span style="color: var(--anthropic-orange);">*</span></label>
                                <input type="text" id="azureSubscriptionId" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" />
                            </div>
                            <div class="input-group">
                                <label>Client ID <span style="color: var(--anthropic-orange);">*</span></label>
                                <input type="text" id="azureClientId" placeholder="Application (client) ID" />
                            </div>
                            <div class="input-group">
                                <label>Client Secret <span style="color: var(--anthropic-orange);">*</span></label>
                                <input type="password" id="azureClientSecret" placeholder="Client secret value" />
                            </div>
                            <div class="input-group">
                                <label>Tenant ID <span style="color: var(--anthropic-orange);">*</span></label>
                                <input type="text" id="azureTenantId" placeholder="Azure AD tenant ID" />
                            </div>
                            <div class="input-group">
                                <label>Resource Group</label>
                                <input type="text" id="azureResourceGroup" placeholder="mcp-server-rg" value="mcp-server-rg" />
                            </div>
                            <div class="input-group">
                                <label>Location</label>
                                <select id="azureLocation" style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 8px; padding: 0.8rem; color: white; width: 100%;">
                                    <option value="eastus">East US</option>
                                    <option value="westus2">West US 2</option>
                                    <option value="westeurope">West Europe</option>
                                    <option value="centralindia">Central India</option>
                                </select>
                            </div>
                        </div>

                        <!-- Remote Tab -->
                        <div id="remote-deploy-tab" class="deployment-tab-content" style="display: none;">
                            <div class="input-group">
                                <label>Host/IP Address <span style="color: var(--anthropic-orange);">*</span></label>
                                <input type="text" id="remoteHost" placeholder="192.168.1.100 or server.example.com" />
                            </div>
                            <div class="input-group">
                                <label>Username <span style="color: var(--anthropic-orange);">*</span></label>
                                <input type="text" id="remoteUsername" placeholder="ubuntu" value="ubuntu" />
                            </div>
                            <div class="input-group">
                                <label>Authentication Method</label>
                                <select id="remoteAuthMethod" onchange="toggleAuthFields()" style="background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 8px; padding: 0.8rem; color: white; width: 100%;">
                                    <option value="password">Password</option>
                                    <option value="key">SSH Key</option>
                                </select>
                            </div>
                            <div class="input-group" id="remotePasswordField">
                                <label>Password</label>
                                <input type="password" id="remotePassword" placeholder="Server password" />
                            </div>
                            <div class="input-group" id="remoteKeyField" style="display: none;">
                                <label>SSH Key Path</label>
                                <input type="text" id="remoteKeyPath" placeholder="/path/to/private/key" />
                                <small style="color: rgba(255, 255, 255, 0.5);">Path to your private SSH key file</small>
                            </div>
                        </div>

                        <!-- Buttons -->
                        <div class="input-buttons">
                            <button class="btn-secondary-custom" onclick="closePublishOnlineModal()">
                                <i class="fas fa-times"></i> Cancel
                            </button>
                            <button class="btn-primary-custom" onclick="startDeployment()" id="deployBtn">
                                <i class="fas fa-rocket"></i> Deploy Now
                            </button>
                        </div>
                    </div>
                </div>
            `;
            document.body.insertAdjacentHTML('beforeend', modalHTML);

            // Add styles for active tab
            const style = document.createElement('style');
            style.textContent = `
                .deployment-tab.active {
                    color: var(--anthropic-orange) !important;
                    border-bottom-color: var(--anthropic-orange) !important;
                }
            `;
            document.head.appendChild(style);
        }

        function switchDeploymentTab(tab) {
            // Update tab buttons
            document.querySelectorAll('.deployment-tab').forEach(btn => {
                btn.classList.remove('active');
                if (btn.dataset.tab === tab) {
                    btn.classList.add('active');
                }
            });

            // Update tab content
            document.querySelectorAll('.deployment-tab-content').forEach(content => {
                content.style.display = 'none';
            });
            document.getElementById(`${tab}-deploy-tab`).style.display = 'block';
        }

        function toggleAuthFields() {
            const method = document.getElementById('remoteAuthMethod').value;
            document.getElementById('remotePasswordField').style.display = method === 'password' ? 'block' : 'none';
            document.getElementById('remoteKeyField').style.display = method === 'key' ? 'block' : 'none';
        }

        function validateDomain(domain) {
            // If domain is empty, it's valid (optional field)
            if (!domain || domain.trim() === '') {
                return { valid: true };
            }

            // Trim whitespace
            domain = domain.trim();

            // Check for valid domain format
            // Domain should not start with http:// or https://
            if (domain.startsWith('http://') || domain.startsWith('https://')) {
                return {
                    valid: false,
                    error: 'Domain should not include http:// or https://. Enter only the domain name (e.g., mcp.example.com)'
                };
            }

            // Check for trailing slash
            if (domain.endsWith('/')) {
                return {
                    valid: false,
                    error: 'Domain should not end with /. Enter only the domain name (e.g., mcp.example.com)'
                };
            }

            // Basic domain validation regex
            // Allows: subdomain.example.com, example.com, sub.domain.example.com
            const domainRegex = /^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;
            
            if (!domainRegex.test(domain)) {
                return {
                    valid: false,
                    error: 'Invalid domain format. Use format like: mcp.example.com or api.yourdomain.com'
                };
            }

            // Check minimum length and must have at least one dot
            if (domain.length < 4 || !domain.includes('.')) {
                return {
                    valid: false,
                    error: 'Domain must be a valid format like: mcp.example.com (must include a domain extension)'
                };
            }

            return { valid: true };
        }

        async function startDeployment() {
            const activeTab = document.querySelector('.deployment-tab.active').dataset.tab;

            try {
                let endpoint, payload;

                if (activeTab === 'aws') {
                    const domain = document.getElementById('awsDomain').value;
                    const domainValidation = validateDomain(domain);
                    
                    if (!domainValidation.valid) {
                        alert('Domain Validation Error: ' + domainValidation.error);
                        return;
                    }

                    endpoint = '/api/deploy/aws';
                    // Get server_path and yaml filename from yaml path
                    let serverPath = null;
                    let yamlFileName = null;
                    if (window.lastGeneratedYamlPath) {
                        // Extract directory and filename from yaml file path
                        const normalizedPath = window.lastGeneratedYamlPath.replace(/\\/g, '/');
                        serverPath = normalizedPath.substring(0, normalizedPath.lastIndexOf('/'));
                        yamlFileName = normalizedPath.substring(normalizedPath.lastIndexOf('/') + 1);
                    } else {
                        // No MCP server files generated yet
                        alert('Warning: No MCP server files found. Please convert APIs to MCP tools first.');
                        return;
                    }

                    // Generate unique server name for API/Swagger deployments
                    let serverName = window.currentServerName;
                    if (!serverName && window.currentApiDomain) {
                        // Extract domain name without protocol and special chars
                        const domainMatch = window.currentApiDomain.match(/(?:https?:\/\/)?([^/:]+)/);
                        if (domainMatch && domainMatch[1]) {
                            const cleanDomain = domainMatch[1].replace(/\./g, '-').replace(/[^a-zA-Z0-9-]/g, '');
                            serverName = cleanDomain.substring(0, 30) + '-mcp';  // Limit to 30 chars + '-mcp'
                        }
                    }
                    if (!serverName) {
                        // Fallback: generate from timestamp
                        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
                        serverName = `api-mcp-${timestamp}`;
                    }

                    payload = {
                        access_key: document.getElementById('awsAccessKey').value,
                        secret_key: document.getElementById('awsSecretKey').value,
                        region: document.getElementById('awsRegion').value || 'ap-south-1',
                        instance_type: document.getElementById('awsInstanceType').value,
                        domain: domain,
                        server_name: serverName,
                        server_type: projectSourceType || 'api',  // Use project source type
                        server_path: serverPath,  // Send directory path where mcp_server_loader.py and YAML files are
                        yaml_file: yamlFileName,   // Send specific YAML filename to copy (not all YAML files)
                        auto_download_logs: document.getElementById('awsAutoDownloadLogs')?.checked || false
                    };

                    // Store credentials for later log download
                    window.lastAwsDeployment = {
                        access_key: payload.access_key,
                        secret_key: payload.secret_key,
                        region: payload.region
                    };
                } else if (activeTab === 'azure') {
                    // Get server_path and yaml filename from yaml path
                    let serverPath = null;
                    let yamlFileName = null;
                    if (window.lastGeneratedYamlPath) {
                        const normalizedPath = window.lastGeneratedYamlPath.replace(/\\/g, '/');
                        serverPath = normalizedPath.substring(0, normalizedPath.lastIndexOf('/'));
                        yamlFileName = normalizedPath.substring(normalizedPath.lastIndexOf('/') + 1);
                    } else {
                        alert('Warning: No MCP server files found. Please convert APIs to MCP tools first.');
                        return;
                    }

                    // Generate unique server name for API/Swagger deployments
                    let serverName = window.currentServerName;
                    if (!serverName && window.currentApiDomain) {
                        const domainMatch = window.currentApiDomain.match(/(?:https?:\/\/)?([^/:]+)/);
                        if (domainMatch && domainMatch[1]) {
                            const cleanDomain = domainMatch[1].replace(/\./g, '-').replace(/[^a-zA-Z0-9-]/g, '');
                            serverName = cleanDomain.substring(0, 30) + '-mcp';
                        }
                    }
                    if (!serverName) {
                        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
                        serverName = `api-mcp-${timestamp}`;
                    }

                    endpoint = '/api/deploy/azure';
                    payload = {
                        subscription_id: document.getElementById('azureSubscriptionId').value,
                        client_id: document.getElementById('azureClientId').value,
                        client_secret: document.getElementById('azureClientSecret').value,
                        tenant_id: document.getElementById('azureTenantId').value,
                        resource_group: document.getElementById('azureResourceGroup').value,
                        location: document.getElementById('azureLocation').value,
                        server_name: serverName,
                        server_type: projectSourceType || 'api',
                        server_path: serverPath,
                        yaml_file: yamlFileName
                    };
                } else if (activeTab === 'remote') {
                    // Get server_path and yaml filename from yaml path
                    let serverPath = null;
                    let yamlFileName = null;
                    if (window.lastGeneratedYamlPath) {
                        const normalizedPath = window.lastGeneratedYamlPath.replace(/\\/g, '/');
                        serverPath = normalizedPath.substring(0, normalizedPath.lastIndexOf('/'));
                        yamlFileName = normalizedPath.substring(normalizedPath.lastIndexOf('/') + 1);
                    } else {
                        alert('Warning: No MCP server files found. Please convert APIs to MCP tools first.');
                        return;
                    }

                    // Generate unique server name for API/Swagger deployments
                    let serverName = window.currentServerName;
                    if (!serverName && window.currentApiDomain) {
                        const domainMatch = window.currentApiDomain.match(/(?:https?:\/\/)?([^/:]+)/);
                        if (domainMatch && domainMatch[1]) {
                            const cleanDomain = domainMatch[1].replace(/\./g, '-').replace(/[^a-zA-Z0-9-]/g, '');
                            serverName = cleanDomain.substring(0, 30) + '-mcp';
                        }
                    }
                    if (!serverName) {
                        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
                        serverName = `api-mcp-${timestamp}`;
                    }

                    endpoint = '/api/deploy/remote';
                    const authMethod = document.getElementById('remoteAuthMethod').value;
                    payload = {
                        host: document.getElementById('remoteHost').value,
                        username: document.getElementById('remoteUsername').value,
                        password: authMethod === 'password' ? document.getElementById('remotePassword').value : null,
                        key_path: authMethod === 'key' ? document.getElementById('remoteKeyPath').value : null,
                        server_name: serverName,
                        server_type: projectSourceType || 'api',
                        server_path: serverPath,
                        yaml_file: yamlFileName
                    };
                }

                // Create a log display modal
                const logHTML = `
                    <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.9); z-index: 999999; padding: 2rem; display: flex; align-items: center; justify-content: center;" id="deployLogModal">
                        <div style="background: linear-gradient(135deg, var(--dark-bg), #1a1f3a); border: 2px solid var(--scikiq-light-blue); border-radius: 16px; max-width: 800px; width: 100%; max-height: 80vh; overflow: hidden; display: flex; flex-direction: column; position: relative;">
                            <button onclick="document.getElementById('deployLogModal').remove()" style="position: absolute; top: 1rem; right: 1rem; background: rgba(255, 255, 255, 0.2); border: none; color: white; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; transition: all 0.3s ease; z-index: 10;" onmouseover="this.style.background='rgba(255, 255, 255, 0.3)'" onmouseout="this.style.background='rgba(255, 255, 255, 0.2)'">
                                <i class="fas fa-times"></i>
                            </button>
                            <div style="padding: 1.5rem; border-bottom: 1px solid rgba(255, 255, 255, 0.1);">
                                <h3 style="margin: 0; color: var(--scikiq-light-blue);">
                                    <i class="fas fa-cloud-upload-alt"></i> Deploying to ${activeTab.toUpperCase()}
                                </h3>
                            </div>
                            <div id="deployLogContent" style="flex: 1; overflow-y: auto; padding: 1.5rem; font-family: 'Fira Code', monospace; font-size: 0.85rem; background: rgba(0, 0, 0, 0.5);"></div>
                            <div style="padding: 1rem; border-top: 1px solid rgba(255, 255, 255, 0.1); display: flex; justify-content: space-between; align-items: center; gap: 1rem;">
                                <div style="display: flex; gap: 0.5rem;">
                                    <button id="downloadLogsBtn" onclick="downloadDisplayedLogs()" style="padding: 0.8rem 1.5rem; background: linear-gradient(135deg, #10B981, #059669); border: none; border-radius: 6px; color: white; cursor: pointer; display: inline-flex;" title="Download deployment logs">
                                        <i class="fas fa-download"></i> Download Logs
                                    </button>
                                </div>
                                <button onclick="document.getElementById('deployLogModal').remove()" style="padding: 0.8rem 1.5rem; background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 6px; color: white; cursor: pointer;">Close</button>
                            </div>
                        </div>
                    </div>
                `;
                document.body.insertAdjacentHTML('beforeend', logHTML);
                const logContent = document.getElementById('deployLogContent');

                function appendLog(message, type = 'info') {
                    const color = type === 'error' ? '#EF4444' : type === 'success' ? '#10B981' : '#E0E0E0';

                    // Extract instance ID from logs if present
                    const instanceIdMatch = message.match(/Instance ID:\s*(i-[a-f0-9]+)/i) || message.match(/Instance\s+(i-[a-f0-9]+)\s+launched/i);
                    if (instanceIdMatch && window.lastAwsDeployment) {
                        window.lastAwsDeployment.instance_id = instanceIdMatch[1];
                        // Show the download/refresh buttons
                        const downloadBtn = document.getElementById('downloadLogsBtn');
                        const refreshBtn = document.getElementById('refreshLogsBtn');
                        if (downloadBtn) downloadBtn.style.display = 'inline-flex';
                        if (refreshBtn) refreshBtn.style.display = 'inline-flex';
                    }

                    // Check if this message contains a permission suggestion block
                    const hasMultipleLines = message.includes('\n');
                    const isPermissionSuggestion = message.includes('Missing Permission') ||
                                                   message.includes('Required IAM Permissions') ||
                                                   message.includes('How to Fix:') ||
                                                   message.includes('Example IAM Policy:') ||
                                                   (message.includes('=') && message.split('=').length > 10);
                    
                    if (hasMultipleLines && isPermissionSuggestion && type === 'error') {
                        // Format as special permission block
                        const formattedMessage = message
                            .replace(/=/g, '─')
                            .replace(/⚠️/g, '⚠️');
                        
                        logContent.innerHTML += `<div style="color: ${color}; margin: 1.5rem 0; padding: 1.5rem; background: rgba(239, 68, 68, 0.15); border: 2px solid ${color}; border-radius: 8px; white-space: pre-wrap; font-family: 'Fira Code', 'Courier New', monospace; font-size: 0.9rem; line-height: 1.8; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); word-wrap: break-word;">${formattedMessage}</div>`;
                    } else if (hasMultipleLines) {
                        // Multi-line message - preserve line breaks
                        logContent.innerHTML += `<div style="color: ${color}; margin-bottom: 0.5rem; white-space: pre-wrap; font-family: 'Fira Code', monospace; word-wrap: break-word;">${message}</div>`;
                    } else {
                        // Single line message
                        logContent.innerHTML += `<div style="color: ${color}; margin-bottom: 0.3rem; white-space: pre-wrap; word-wrap: break-word;">${message}</div>`;
                    }
                    logContent.scrollTop = logContent.scrollHeight;
                }

                appendLog(`[${new Date().toLocaleTimeString()}] Starting deployment to ${activeTab.toUpperCase()}...`);
                appendLog(`[${new Date().toLocaleTimeString()}] Connecting to API endpoint: ${endpoint}`);

                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    appendLog(`[${new Date().toLocaleTimeString()}] ERROR: ${response.status} - ${response.statusText}`, 'error');
                    appendLog(`[${new Date().toLocaleTimeString()}] Details: ${errorText}`, 'error');

                    // Try to parse as JSON for better error display
                    try {
                        const errorJson = JSON.parse(errorText);
                        appendLog(`[${new Date().toLocaleTimeString()}] ${errorJson.error || errorJson.message || 'Unknown error'}`, 'error');
                    } catch (e) {
                        appendLog(`[${new Date().toLocaleTimeString()}] Raw error: ${errorText}`, 'error');
                    }
                    return;
                }

                // Stream logs if response is text/plain
                if (response.headers.get('content-type')?.includes('text/plain')) {
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();

                    let buffer = '';
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;

                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\n');
                        buffer = lines.pop(); // Keep incomplete line in buffer

                        lines.forEach(line => {
                            if (line.trim()) {
                                const isError = line.includes('[ERROR]') || line.includes('ERROR:');
                                const isSuccess = line.includes('[SUCCESS]') || line.includes('SUCCESS:');
                                appendLog(line, isError ? 'error' : isSuccess ? 'success' : 'info');
                            }
                        });
                    }

                    // Process remaining buffer
                    if (buffer.trim()) {
                        const isError = buffer.includes('[ERROR]') || buffer.includes('ERROR:');
                        const isSuccess = buffer.includes('[SUCCESS]') || buffer.includes('SUCCESS:');
                        appendLog(buffer, isError ? 'error' : isSuccess ? 'success' : 'info');
                    }
                } else {
                    // Handle JSON response
                    const result = await response.json();
                    if (result.success) {
                        appendLog(`[${new Date().toLocaleTimeString()}] Deployment completed successfully!`, 'success');
                        if (result.message) appendLog(result.message, 'success');
                    } else {
                        appendLog(`[${new Date().toLocaleTimeString()}] Deployment failed: ${result.error}`, 'error');
                    }
                }

                appendLog(`[${new Date().toLocaleTimeString()}] Deployment process finished.`, 'success');

            } catch (error) {
                console.error('Deployment error:', error);
                const logContent = document.getElementById('deployLogContent');
                if (logContent) {
                    logContent.innerHTML += `<div style="color: #EF4444; margin-bottom: 0.5rem;">[${new Date().toLocaleTimeString()}] ERROR: ${error.message}</div>`;
                } else {
                    alert('Deployment error: ' + error.message);
                }
            }
        }

        function closePublishOnlineModal() {
            const modal = document.getElementById('publishOnlineModal');
            if (modal) modal.remove();
        }

        // Download logs displayed in the deployment popup
        function downloadDisplayedLogs() {
            const logContent = document.getElementById('deployLogContent');
            if (!logContent) {
                alert('No logs to download');
                return;
            }

            // Get text content from the log div
            const logsText = logContent.innerText || logContent.textContent;

            if (!logsText.trim()) {
                alert('No logs to download');
                return;
            }

            // Create filename with timestamp
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
            const filename = `deployment_logs_${timestamp}.txt`;

            // Create and download the file
            const blob = new Blob([logsText], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }

        // Download deployment logs from EC2 instance (legacy - kept for compatibility)
        async function downloadDeploymentLogs() {
            if (!window.lastAwsDeployment || !window.lastAwsDeployment.instance_id) {
                alert('No deployment instance found. Please deploy first.');
                return;
            }

            const { instance_id, access_key, secret_key, region } = window.lastAwsDeployment;
            const downloadBtn = document.getElementById('downloadLogsBtn');

            try {
                if (downloadBtn) {
                    downloadBtn.disabled = true;
                    downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Downloading...';
                }

                const response = await fetch('/api/deploy/aws/logs/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        instance_id: instance_id,
                        access_key: access_key,
                        secret_key: secret_key,
                        region: region
                    })
                });

                if (response.ok) {
                    // Get filename from Content-Disposition header or create one
                    const contentDisposition = response.headers.get('Content-Disposition');
                    let filename = `deployment_logs_${instance_id}.txt`;
                    if (contentDisposition) {
                        const match = contentDisposition.match(/filename="?([^"]+)"?/);
                        if (match) filename = match[1];
                    }

                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    window.URL.revokeObjectURL(url);
                    a.remove();
                } else {
                    const error = await response.json();
                    alert('Failed to download logs: ' + (error.error || 'Unknown error'));
                }
            } catch (error) {
                console.error('Error downloading logs:', error);
                alert('Error downloading logs: ' + error.message);
            } finally {
                if (downloadBtn) {
                    downloadBtn.disabled = false;
                    downloadBtn.innerHTML = '<i class="fas fa-download"></i> Download Logs';
                }
            }
        }

        // Refresh/fetch logs from EC2 instance
        async function refreshDeploymentLogs() {
            if (!window.lastAwsDeployment || !window.lastAwsDeployment.instance_id) {
                alert('No deployment instance found. Please deploy first.');
                return;
            }

            const { instance_id, access_key, secret_key, region } = window.lastAwsDeployment;
            const refreshBtn = document.getElementById('refreshLogsBtn');
            const logContent = document.getElementById('deployLogContent');

            try {
                if (refreshBtn) {
                    refreshBtn.disabled = true;
                    refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Fetching...';
                }

                if (logContent) {
                    logContent.innerHTML += `<div style="color: #3B82F6; margin: 1rem 0; padding: 0.5rem; background: rgba(59, 130, 246, 0.1); border-radius: 4px;">[${new Date().toLocaleTimeString()}] Fetching latest logs from EC2...</div>`;
                    logContent.scrollTop = logContent.scrollHeight;
                }

                const response = await fetch('/api/deploy/aws/logs', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        instance_id: instance_id,
                        access_key: access_key,
                        secret_key: secret_key,
                        region: region,
                        wait_for_completion: false
                    })
                });

                if (response.ok && response.headers.get('content-type')?.includes('text/plain')) {
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();

                    let buffer = '';
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) break;

                        buffer += decoder.decode(value, { stream: true });
                        const lines = buffer.split('\n');
                        buffer = lines.pop();

                        lines.forEach(line => {
                            if (line.trim() && logContent) {
                                const isError = line.includes('[ERROR]');
                                const isSuccess = line.includes('[SUCCESS]');
                                const color = isError ? '#EF4444' : isSuccess ? '#10B981' : '#E0E0E0';
                                logContent.innerHTML += `<div style="color: ${color}; margin-bottom: 0.3rem; white-space: pre-wrap;">${line}</div>`;
                                logContent.scrollTop = logContent.scrollHeight;
                            }
                        });
                    }

                    if (buffer.trim() && logContent) {
                        logContent.innerHTML += `<div style="color: #E0E0E0; margin-bottom: 0.3rem; white-space: pre-wrap;">${buffer}</div>`;
                    }
                } else {
                    const error = await response.json();
                    if (logContent) {
                        logContent.innerHTML += `<div style="color: #EF4444; margin-bottom: 0.5rem;">[${new Date().toLocaleTimeString()}] Failed to fetch logs: ${error.error || 'Unknown error'}</div>`;
                    }
                }
            } catch (error) {
                console.error('Error refreshing logs:', error);
                if (logContent) {
                    logContent.innerHTML += `<div style="color: #EF4444; margin-bottom: 0.5rem;">[${new Date().toLocaleTimeString()}] Error: ${error.message}</div>`;
                }
            } finally {
                if (refreshBtn) {
                    refreshBtn.disabled = false;
                    refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Refresh Logs';
                }
            }
        }

        // Database Deployment Method Switching
        function switchDeploymentMethod(method) {
            // Update button styles
            document.querySelectorAll('.deploy-method-btn').forEach(btn => {
                if (btn.dataset.method === method) {
                    btn.style.background = 'linear-gradient(135deg, var(--scikiq-light-blue), #0891B2)';
                    btn.style.border = '3px solid var(--scikiq-light-blue)';
                } else {
                    btn.style.background = 'rgba(124, 58, 237, 0.2)';
                    btn.style.border = '3px solid transparent';
                }
            });

            // Show/hide content
            if (method === 'local') {
                document.getElementById('local-deployment-content').style.display = 'block';
                document.getElementById('online-deployment-content').style.display = 'none';
            } else {
                document.getElementById('local-deployment-content').style.display = 'none';
                document.getElementById('online-deployment-content').style.display = 'block';
            }
        }

        function switchOnlineDeployTab(tab) {
            // Update tab styles
            document.querySelectorAll('.online-deploy-tab').forEach(btn => {
                if (btn.dataset.tab === tab) {
                    btn.style.borderBottomColor = 'var(--anthropic-orange)';
                    btn.style.color = 'var(--anthropic-orange)';
                } else {
                    btn.style.borderBottomColor = 'transparent';
                    btn.style.color = 'rgba(255, 255, 255, 0.6)';
                }
            });

            // Show/hide tab content
            document.querySelectorAll('.online-tab-content').forEach(content => {
                content.style.display = 'none';
            });
            document.getElementById(`${tab}-online-tab`).style.display = 'block';
        }

        async function deployDatabaseOnline(platform, configPath, serverPath, serverName) {
            console.log(`[DEPLOY] Starting deployment to ${platform} for ${serverName}`);
            console.log(`[DEPLOY] Config path: ${configPath}`);
            console.log(`[DEPLOY] Server path: ${serverPath}`);

            try {
                let endpoint, payload;

                // Prepare payload based on platform
                if (platform === 'aws') {
                    const domain = document.getElementById('dbAwsDomain')?.value || '';
                    const domainValidation = validateDomain(domain);
                    
                    if (!domainValidation.valid) {
                        alert('Domain Validation Error: ' + domainValidation.error);
                        return;
                    }

                    endpoint = '/api/deploy/aws';
                    payload = {
                        access_key: document.getElementById('dbAwsAccessKey').value,
                        secret_key: document.getElementById('dbAwsSecretKey').value,
                        region: document.getElementById('dbAwsRegion').value || 'ap-south-1',
                        instance_type: document.getElementById('dbAwsInstanceType').value || 't2.micro',
                        server_type: 'database',
                        config_path: configPath,
                        server_path: serverPath,
                        server_name: serverName,
                        domain: domain
                    };
                } else if (platform === 'azure') {
                    endpoint = '/api/deploy/azure';
                    payload = {
                        subscription_id: document.getElementById('dbAzureSubscriptionId').value,
                        client_id: document.getElementById('dbAzureClientId').value,
                        client_secret: '', // Simplified for now
                        tenant_id: '',
                        resource_group: 'mcp-server-rg',
                        location: 'eastus',
                        server_type: 'database',
                        config_path: configPath,
                        server_path: serverPath,
                        server_name: serverName
                    };
                } else if (platform === 'remote') {
                    endpoint = '/api/deploy/remote';
                    payload = {
                        host: document.getElementById('dbRemoteHost').value,
                        username: document.getElementById('dbRemoteUsername').value,
                        password: document.getElementById('dbRemotePassword').value,
                        server_type: 'database',
                        config_path: configPath,
                        server_path: serverPath,
                        server_name: serverName
                    };
                }

                console.log(`[DEPLOY] Calling endpoint: ${endpoint}`);
                console.log(`[DEPLOY] Payload:`, payload);

                // Create a log display modal
                const logHTML = `
                    <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.9); z-index: 999999; padding: 2rem; display: flex; align-items: center; justify-content: center;" id="deployLogModal">
                        <div style="background: linear-gradient(135deg, var(--dark-bg), #1a1f3a); border: 2px solid var(--scikiq-light-blue); border-radius: 16px; max-width: 800px; width: 100%; max-height: 80vh; overflow: hidden; display: flex; flex-direction: column; position: relative;">
                            <button onclick="document.getElementById('deployLogModal').remove()" style="position: absolute; top: 1rem; right: 1rem; background: rgba(255, 255, 255, 0.2); border: none; color: white; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; transition: all 0.3s ease; z-index: 10;" onmouseover="this.style.background='rgba(255, 255, 255, 0.3)'" onmouseout="this.style.background='rgba(255, 255, 255, 0.2)'">
                                <i class="fas fa-times"></i>
                            </button>
                            <div style="padding: 1.5rem; border-bottom: 1px solid rgba(255, 255, 255, 0.1);">
                                <h3 style="margin: 0; color: var(--scikiq-light-blue);">
                                    <i class="fas fa-cloud-upload-alt"></i> Deploying to ${platform.toUpperCase()}
                                </h3>
                            </div>
                            <div id="deployLogContent" style="flex: 1; overflow-y: auto; padding: 1.5rem; font-family: 'Fira Code', monospace; font-size: 0.85rem; background: rgba(0, 0, 0, 0.5);"></div>
                            <div style="padding: 1rem; border-top: 1px solid rgba(255, 255, 255, 0.1); display: flex; justify-content: flex-end;">
                                <button onclick="document.getElementById('deployLogModal').remove()" style="padding: 0.8rem 1.5rem; background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 6px; color: white; cursor: pointer;">Close</button>
                            </div>
                        </div>
                    </div>
                `;
                document.body.insertAdjacentHTML('beforeend', logHTML);
                const logContent = document.getElementById('deployLogContent');

                function appendLog(message, type = 'info') {
                    const color = type === 'error' ? '#EF4444' : type === 'success' ? '#10B981' : '#E0E0E0';

                    // Check if this message contains a permission suggestion block (has multiple lines with formatting)
                    const hasMultipleLines = message.includes('\n');
                    const isPermissionSuggestion = message.includes('Missing Permission') ||
                                                   message.includes('Required IAM Permissions') ||
                                                   message.includes('How to Fix:') ||
                                                   message.includes('Example IAM Policy:') ||
                                                   (message.includes('=') && message.split('=').length > 10);

                    if (hasMultipleLines && isPermissionSuggestion && type === 'error') {
                        // This is a multi-line permission suggestion - format it as a special block
                        const formattedMessage = message
                            .replace(/=/g, '─')
                            .replace(/⚠️/g, '⚠️');

                        logContent.innerHTML += `<div style="color: ${color}; margin: 1.5rem 0; padding: 1.5rem; background: rgba(239, 68, 68, 0.15); border: 2px solid ${color}; border-radius: 8px; white-space: pre-wrap; font-family: 'Fira Code', 'Courier New', monospace; font-size: 0.9rem; line-height: 1.8; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3); word-wrap: break-word;">${formattedMessage}</div>`;
                    } else if (hasMultipleLines) {
                        // Multi-line message - preserve line breaks
                        logContent.innerHTML += `<div style="color: ${color}; margin-bottom: 0.5rem; white-space: pre-wrap; font-family: 'Fira Code', monospace; word-wrap: break-word;">${message}</div>`;
                    } else {
                        // Single line message
                        logContent.innerHTML += `<div style="color: ${color}; margin-bottom: 0.3rem; white-space: pre-wrap; word-wrap: break-word;">${message}</div>`;
                    }
                    logContent.scrollTop = logContent.scrollHeight;
                }

                appendLog(`[${new Date().toLocaleTimeString()}] Starting deployment to ${platform.toUpperCase()}...`);
                appendLog(`[${new Date().toLocaleTimeString()}] Connecting to API endpoint: ${endpoint}`);

                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                console.log(`[DEPLOY] Response status: ${response.status}`);
                console.log(`[DEPLOY] Response headers:`, response.headers);

                if (!response.ok) {
                    const errorText = await response.text();
                    console.error(`[DEPLOY] Error response:`, errorText);
                    appendLog(`[${new Date().toLocaleTimeString()}] ERROR: ${response.status} - ${response.statusText}`, 'error');
                    appendLog(`[${new Date().toLocaleTimeString()}] Details: ${errorText}`, 'error');

                    // Try to parse as JSON for better error display
                    try {
                        const errorJson = JSON.parse(errorText);
                        appendLog(`[${new Date().toLocaleTimeString()}] ${errorJson.error || errorJson.message || 'Unknown error'}`, 'error');
                    } catch (e) {
                        appendLog(`[${new Date().toLocaleTimeString()}] Raw error: ${errorText}`, 'error');
                    }
                    return;
                }

                // Stream logs if response is text/plain
                if (response.headers.get('content-type')?.includes('text/plain')) {
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();

                    let buffer = '';
                    while (true) {
                        const { done, value } = await reader.read();
                        if (done) {
                            // Process any remaining buffer
                            if (buffer.trim()) {
                                const lines = buffer.split('\n').filter(l => l.trim());
                                lines.forEach(line => {
                                    const logType = line.includes('[ERROR]') ? 'error' : line.includes('[SUCCESS]') ? 'success' : 'info';
                                    const cleanLine = line.replace(/^\[(ERROR|INFO|WARNING|SUCCESS|LOG)\]\s*/, '');
                                    appendLog(cleanLine, logType);
                                });
                            }
                            break;
                        }

                        const text = decoder.decode(value, { stream: true });
                        buffer += text;
                        
                        // Process complete lines (ending with \n)
                        const lines = buffer.split('\n');
                        buffer = lines.pop() || ''; // Keep incomplete line in buffer
                        
                        lines.forEach(line => {
                            if (line.trim()) {
                                const logType = line.includes('[ERROR]') ? 'error' : line.includes('[SUCCESS]') ? 'success' : 'info';
                                // Extract the log level and content
                                const match = line.match(/^\[(ERROR|INFO|WARNING|SUCCESS|LOG)\]\s*(.*)$/);
                                if (match) {
                                    const level = match[1];
                                    const content = match[2];
                                    
                                    // Check if this is a permission suggestion (multi-line with special formatting)
                                    const isPermissionSuggestion = content.includes('Missing Permission') || 
                                                                   content.includes('Required IAM Permissions') ||
                                                                   content.includes('How to Fix:') ||
                                                                   (content.includes('=') && content.split('=').length > 5);
                                    
                                    if (isPermissionSuggestion && level === 'ERROR') {
                                        // This is likely the start of a permission suggestion
                                        // The full message might be in content if it's multi-line
                                        appendLog(content, logType);
                                    } else {
                                        // Regular log entry
                                        appendLog(`[${new Date().toLocaleTimeString()}] ${content}`, logType);
                                    }
                                } else {
                                    // Line doesn't match expected format, display as-is
                                    appendLog(line, logType);
                                }
                            }
                        });
                    }

                    appendLog(`[${new Date().toLocaleTimeString()}] Deployment process completed`, 'success');
                } else {
                    const result = await response.json();
                    if (result.error) {
                        appendLog(`[${new Date().toLocaleTimeString()}] ERROR: ${result.error}`, 'error');
                    } else {
                        appendLog(`[${new Date().toLocaleTimeString()}] Deployment successful!`, 'success');
                        appendLog(`[${new Date().toLocaleTimeString()}] Result: ${JSON.stringify(result)}`, 'success');
                    }
                }

            } catch (error) {
                console.error(`[DEPLOY] Exception:`, error);
                const logContent = document.getElementById('deployLogContent');
                if (logContent) {
                    logContent.innerHTML += `<div style="color: #EF4444; margin-bottom: 0.3rem;">[${new Date().toLocaleTimeString()}] EXCEPTION: ${error.message}</div>`;
                    logContent.innerHTML += `<div style="color: #EF4444; margin-bottom: 0.3rem;">[${new Date().toLocaleTimeString()}] Stack: ${error.stack}</div>`;
                } else {
                    alert(`Deployment error: ${error.message}\n\nCheck console for details.`);
                }
            }
        }

        // ==================== MCP DEPLOYMENT FUNCTIONS (SWAGGER & CODEBASE) ====================
        
        async function deployMCPLocal(serverPath, filename) {
            try {
                const serverName = document.getElementById('mcpServerName')?.value || 'scikiq-mcp-autoAPI';
                
                const response = await fetch('/api/deploy-mcp-local', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        server_path: serverPath,
                        server_name: serverName,
                        config: selectedSwaggerConfig || selectedProjectConfig
                    })
                });
                
                const result = await response.json();
                if (result.success) {
                    alert('✅ MCP Server deployed locally!\n\nRestart Claude Desktop to see your tools.');
                } else {
                    alert('❌ Deployment failed: ' + result.error);
                }
            } catch (error) {
                alert('❌ Deployment error: ' + error.message);
            }
        }

        function showOnlineDeploymentModal(serverPath, filename) {
            // Close the MCP setup modal first
            const setupModal = document.querySelector('[style*="position: fixed"][style*="z-index: 10000"]');
            if (setupModal) setupModal.remove();
            
            // Show deployment modal similar to database MCP
            const modalHTML = `
                <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.9); z-index: 10001; display: flex; align-items: center; justify-content: center; padding: 2rem; overflow-y: auto;">
                    <div style="background: linear-gradient(135deg, rgba(0, 48, 135, 0.98), rgba(26, 31, 58, 0.98)); border: 2px solid var(--scikiq-light-blue); border-radius: 16px; max-width: 600px; width: 100%; max-height: 90vh; overflow-y: auto; position: relative;">
                        <div style="background: linear-gradient(135deg, var(--scikiq-light-blue), #0891B2); padding: 2rem; border-radius: 14px 14px 0 0; position: relative;">
                            <button onclick="this.closest('[style*=fixed]').remove()" style="position: absolute; top: 1rem; right: 1rem; background: rgba(255, 255, 255, 0.2); border: none; color: white; width: 36px; height: 36px; border-radius: 50%; cursor: pointer; font-size: 1.2rem; display: flex; align-items: center; justify-content: center; transition: all 0.3s ease;" onmouseover="this.style.background='rgba(255, 255, 255, 0.3)'" onmouseout="this.style.background='rgba(255, 255, 255, 0.2)'">
                                <i class="fas fa-times"></i>
                            </button>
                            <h2 style="margin: 0; color: white; font-size: 1.8rem;">
                                <i class="fas fa-cloud"></i> Deploy MCP Server Online
                            </h2>
                        </div>
                        
                        <div style="padding: 2rem;">
                            <p style="color: rgba(255, 255, 255, 0.8); margin-bottom: 1.5rem;">
                                Deploy your MCP server to a cloud provider or remote server
                            </p>
                            
                            <!-- Deployment Options -->
                            <div style="display: grid; gap: 1rem;">
                                <button onclick="deployToAWS('${serverPath}', '${filename}')" style="padding: 1.5rem; background: rgba(255, 153, 0, 0.1); border: 2px solid #FF9900; border-radius: 8px; color: white; cursor: pointer; text-align: left; transition: all 0.3s ease;" onmouseover="this.style.background='rgba(255, 153, 0, 0.2)'" onmouseout="this.style.background='rgba(255, 153, 0, 0.1)'">
                                    <div style="display: flex; align-items: center; gap: 1rem;">
                                        <i class="fab fa-aws" style="font-size: 2rem;"></i>
                                        <div>
                                            <div style="font-weight: 700; font-size: 1.1rem;">AWS EC2</div>
                                            <div style="font-size: 0.9rem; opacity: 0.8;">Deploy to Amazon Web Services</div>
                                        </div>
                                    </div>
                                </button>
                                
                                <button onclick="deployToAzure('${serverPath}', '${filename}')" style="padding: 1.5rem; background: rgba(0, 120, 215, 0.1); border: 2px solid #0078D7; border-radius: 8px; color: white; cursor: pointer; text-align: left; transition: all 0.3s ease;" onmouseover="this.style.background='rgba(0, 120, 215, 0.2)'" onmouseout="this.style.background='rgba(0, 120, 215, 0.1)'">
                                    <div style="display: flex; align-items: center; gap: 1rem;">
                                        <i class="fab fa-microsoft" style="font-size: 2rem;"></i>
                                        <div>
                                            <div style="font-weight: 700; font-size: 1.1rem;">Azure VM</div>
                                            <div style="font-size: 0.9rem; opacity: 0.8;">Deploy to Microsoft Azure</div>
                                        </div>
                                    </div>
                                </button>
                                
                                <button onclick="deployToRemote('${serverPath}', '${filename}')" style="padding: 1.5rem; background: rgba(124, 58, 237, 0.1); border: 2px solid #7C3AED; border-radius: 8px; color: white; cursor: pointer; text-align: left; transition: all 0.3s ease;" onmouseover="this.style.background='rgba(124, 58, 237, 0.2)'" onmouseout="this.style.background='rgba(124, 58, 237, 0.1)'">
                                    <div style="display: flex; align-items: center; gap: 1rem;">
                                        <i class="fas fa-server" style="font-size: 2rem;"></i>
                                        <div>
                                            <div style="font-weight: 700; font-size: 1.1rem;">Remote Server (SSH)</div>
                                            <div style="font-size: 0.9rem; opacity: 0.8;">Deploy to any server via SSH</div>
                                        </div>
                                    </div>
                                </button>
                            </div>
                            
                            <button onclick="this.closest('[style*=fixed]').remove()" style="width: 100%; margin-top: 1.5rem; padding: 1rem; background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 8px; color: white; font-weight: 600; cursor: pointer;">
                                <i class="fas fa-times"></i> Cancel
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.insertAdjacentHTML('beforeend', modalHTML);
        }

        async function deployToAWS(serverPath, filename) {
            // Close current modal and show publish online modal with AWS tab
            const currentModal = document.querySelector('[style*="position: fixed"][style*="z-index: 10001"]');
            if (currentModal) currentModal.remove();
            
            showPublishOnlineModal();
            // Wait for modal to render, then switch to AWS tab
            setTimeout(() => {
                switchDeploymentTab('aws');
            }, 100);
        }

        async function deployToAzure(serverPath, filename) {
            // Close current modal and show publish online modal with Azure tab
            const currentModal = document.querySelector('[style*="position: fixed"][style*="z-index: 10001"]');
            if (currentModal) currentModal.remove();
            
            showPublishOnlineModal();
            // Wait for modal to render, then switch to Azure tab
            setTimeout(() => {
                switchDeploymentTab('azure');
            }, 100);
        }

        async function deployToRemote(serverPath, filename) {
            // Close current modal and show publish online modal with Remote tab
            const currentModal = document.querySelector('[style*="position: fixed"][style*="z-index: 10001"]');
            if (currentModal) currentModal.remove();
            
            showPublishOnlineModal();
            // Wait for modal to render, then switch to Remote tab
            setTimeout(() => {
                switchDeploymentTab('remote');
            }, 100);
        }
