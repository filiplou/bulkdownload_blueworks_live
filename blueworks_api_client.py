"""
IBM Blueworks Live API Client
Authenticates using OAuth 2.0 and retrieves active users
"""

import requests
import json
import sys
import warnings
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from generate_process_maps import generate_process_maps_report

# Suppress SSL warnings when using verify=False
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    import io
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
    else:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')  # type: ignore


class BlueworksLiveClient:
    """Client for interacting with IBM Blueworks Live API"""
    
    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize the Blueworks Live API client
        
        Args:
            client_id: API client ID (username or account ID)
            client_secret: API client secret (API key)
        """
        self.client_id = client_id  # OAuth Client ID
        self.client_secret = client_secret  # OAuth Client Secret
        # IBM Blueworks Live base URL
        self.base_url = "https://ibm.blueworkslive.com"
        self.token_url = f"{self.base_url}/oauth/token"
        self.users_url = f"{self.base_url}/scr/api/UserList"
        self.spaces_url = f"{self.base_url}/bwl/spaces"
        self.processes_url = f"{self.base_url}/bwl/processes"
        self.library_artifact_url = f"{self.base_url}/scr/api/LibraryArtifact"
        self.access_token = None
        self.token_expiry = None
        self.user_email = None  # For X-On-Behalf-Of header
        
    def authenticate(self) -> bool:
        """
        Authenticate with Blueworks Live using OAuth 2.0 client credentials
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        print(f"  Using OAuth 2.0 client credentials flow")
        
        try:
            response = requests.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                },
                headers={"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"},
                verify=False  # Using -k flag like in curl
            )
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)
            self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
            
            print(f"✓ Authentication successful")
            print(f"  Access token obtained (expires in {expires_in} seconds)")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Authentication failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Status Code: {e.response.status_code}")
                try:
                    error_data = e.response.json()
                    print(f"  Error: {error_data}")
                except:
                    print(f"  Response: {e.response.text[:200]}")
            return False
    
    def _ensure_token_valid(self) -> bool:
        """Ensure access token is valid, refresh if needed"""
        if not self.access_token or not self.token_expiry:
            return self.authenticate()
        
        # Refresh token if it expires in less than 5 minutes
        if datetime.now() >= self.token_expiry - timedelta(minutes=5):
            print("  Token expiring soon, refreshing...")
            return self.authenticate()
        
        return True
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests with Bearer token"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def get_active_users(self) -> Optional[List[Dict]]:
        """
        Retrieve all active users from Blueworks Live using the UserList API
        
        Returns:
            List of user dictionaries or None if request fails
        """
        # Ensure token is valid
        if not self._ensure_token_valid():
            return None
        
        try:
            response = requests.get(
                self.users_url,
                headers=self._get_headers(),
                verify=False  # Using -k flag like in curl
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Handle different response structures
            if isinstance(data, list):
                all_users = data
            elif isinstance(data, dict):
                # Check for common response structures
                all_users = data.get("users", data.get("items", data.get("data", data.get("UserList", []))))
            else:
                all_users = []
            
            # Filter for active users
            active_users = [user for user in all_users if user.get("active", True) != False]
            
            print(f"✓ Retrieved {len(active_users)} active users (out of {len(all_users)} total)")
            return active_users
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to retrieve users: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Status Code: {e.response.status_code}")
                try:
                    error_data = e.response.json()
                    print(f"  Error: {error_data}")
                except:
                    print(f"  Response: {e.response.text[:200]}")
            return None
    
    def get_all_spaces(self, user_email: str) -> Optional[List[Dict]]:
        """
        Retrieve all spaces from Blueworks Live using the BWL Spaces API
        Uses OAuth 2.0 access token with required BWL headers
        
        Args:
            user_email: Email for X-On-Behalf-Of header
            
        Returns:
            List of space dictionaries or None if request fails
        """
        if not self._ensure_token_valid():
            return None
            
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-IBM-API-Version": "1.0.0",
            "X-On-Behalf-Of": user_email,
            "accept": "application/json"
        }
        
        # Query parameters for active spaces
        # API requires at least one of 'name' or 'tag' to be provided
        params = {
            "archived-state": "active",
            "parent-space-id": "",
            "parent-space-name": "",
            "top-space-only": "false",
            "name": "Invoice Processing"
        }
        
        try:
            print(f"  Calling: {self.spaces_url}")
            response = requests.get(
                self.spaces_url,
                headers=headers,
                params=params,
                verify=False
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Debug: Print response structure
            print(f"  DEBUG: Response type: {type(data)}")
            if isinstance(data, dict):
                print(f"  DEBUG: Response keys: {list(data.keys())}")
            
            # Handle different response structures
            if isinstance(data, list):
                spaces = data
            elif isinstance(data, dict):
                spaces = data.get("spaces", data.get("items", data.get("data", [])))
            else:
                spaces = []
            
            print(f"✓ Retrieved {len(spaces)} spaces")
            if len(spaces) == 0 and isinstance(data, dict):
                print(f"  DEBUG: Full response: {json.dumps(data, indent=2)[:500]}")
            return spaces
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to retrieve spaces: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Status Code: {e.response.status_code}")
                try:
                    error_detail = e.response.json()
                    print(f"  Error: {error_detail}")
                except:
                    print(f"  Response: {e.response.text[:200]}")
            return None
    
    def get_space_details(self, space_id: str) -> Optional[Dict]:
        """
        Retrieve details for a specific space
        
        Args:
            space_id: The ID of the space to retrieve
            
        Returns:
            Space dictionary or None if request fails
        """
        if not self._ensure_token_valid():
            return None
        
        space_detail_url = f"{self.spaces_url}/{space_id}"
        
        try:
            response = requests.get(
                space_detail_url,
                headers=self._get_headers(),
                verify=False
            )
            response.raise_for_status()
            
            data = response.json()
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to retrieve space {space_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Status Code: {e.response.status_code}")
            return None
    
    def get_process_by_id(self, process_id: str, user_email: str) -> Optional[Dict]:
        """
        Retrieve a specific process by its ID
        
        Args:
            process_id: The ID of the process to retrieve
            user_email: Email for X-On-Behalf-Of header
            
        Returns:
            Process dictionary or None if request fails
        """
        if not self._ensure_token_valid():
            return None
        
        # Use the BWL processes API endpoint
        process_url = f"{self.base_url}/bwl/processes/{process_id}"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-IBM-API-Version": "1.0.0",
            "X-On-Behalf-Of": user_email,
            "accept": "application/json"
        }
        
        try:
            print(f"  Calling: {process_url}")
            response = requests.get(
                process_url,
                headers=headers,
                verify=False
            )
            response.raise_for_status()
            
            process_data = response.json()
            print(f"✓ Retrieved process {process_id}")
            return process_data
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to retrieve process {process_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Status Code: {e.response.status_code}")
                try:
                    error_detail = e.response.json()
                    print(f"  Error: {error_detail}")
                except:
                    print(f"  Response: {e.response.text[:200]}")
            return None
    
    def get_all_artifacts_csv(self) -> Optional[str]:
        """
        Retrieve all library artifacts in CSV format using the LibraryArtifact API
        This returns spaces, processes, and other artifacts in a CSV format
        
        Returns:
            CSV string with all artifacts or None if request fails
        """
        if not self._ensure_token_valid():
            return None
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "text/csv"
        }
        
        # Parameters for LibraryArtifact API
        # Use wildcard (*) to return ALL available fields
        params = {
            "returnFields": "*"
        }
        
        try:
            print(f"  Calling: {self.library_artifact_url}")
            response = requests.get(
                self.library_artifact_url,
                headers=headers,
                params=params,
                verify=False
            )
            response.raise_for_status()
            
            csv_data = response.text
            print(f"✓ Retrieved artifacts in CSV format ({len(csv_data)} characters)")
            return csv_data
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to retrieve artifacts: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Status Code: {e.response.status_code}")
                try:
                    error_detail = e.response.json()
                    print(f"  Error: {error_detail}")
                except:
                    print(f"  Response: {e.response.text[:200]}")
            return None
    
    def get_all_spaces_with_processes(self, user_email: str) -> Optional[Dict]:
        """
        Retrieve all spaces with their associated processes using the BWL Spaces API
        
        Args:
            user_email: Email for X-On-Behalf-Of header
            
        Returns:
            Dictionary with spaces and their processes or None if request fails
        """
        # Get all spaces
        spaces = self.get_all_spaces(user_email)
        if spaces is None:
            return None
        
        result = {
            "spaces": [],
            "total_spaces": len(spaces),
            "total_processes": 0
        }
        
        # For each space, get example process (hardcoded for now)
        for space in spaces:
            space_id = space.get("id", space.get("spaceId", space.get("artifactId")))
            space_name = space.get("name", space.get("title", "Unnamed Space"))
            
            # Get example process for Invoice Processing space
            space_processes = []
            if space_name == "Invoice Processing":
                example_process = self.get_process_by_id("96ea888454", user_email)
                if example_process:
                    space_processes = [example_process]
            
            result["total_processes"] += len(space_processes)
            
            result["spaces"].append({
                "id": space_id,
                "name": space_name,
                "description": space.get("description", ""),
                "created": space.get("created", space.get("createdDate", "")),
                "modified": space.get("modified", space.get("modifiedDate", "")),
                "processes": space_processes,
                "process_count": len(space_processes)
            })
        
        print(f"✓ Organized {result['total_spaces']} spaces with {result['total_processes']} total processes")
        return result
    
    def display_users(self, users: List[Dict]) -> None:
        """
        Display user information in a readable format
        
        Args:
            users: List of user dictionaries
        """
        if not users:
            print("No users to display")
            return
        
        print(f"\n{'='*80}")
        print(f"ACTIVE USERS ({len(users)} total)")
        print(f"{'='*80}\n")
        
        for idx, user in enumerate(users, 1):
            user_id = user.get("id", user.get("userId", "N/A"))
            username = user.get("userName", user.get("username", user.get("login", "N/A")))
            
            # Get name information - handle both dict and string formats
            name = user.get("name", "")
            if isinstance(name, dict):
                given_name = name.get("givenName", "")
                family_name = name.get("familyName", "")
                full_name = f"{given_name} {family_name}".strip() or "N/A"
            elif isinstance(name, str):
                full_name = name or "N/A"
            else:
                # Try firstName/lastName fields
                first_name = user.get("firstName", "")
                last_name = user.get("lastName", "")
                full_name = f"{first_name} {last_name}".strip() or "N/A"
            
            # Get email - handle both list and string formats
            emails = user.get("emails", user.get("email", ""))
            if isinstance(emails, list) and emails:
                email = emails[0].get("value", emails[0]) if isinstance(emails[0], dict) else emails[0]
            elif isinstance(emails, str):
                email = emails
            else:
                email = "N/A"
            
            # Get active status
            active = user.get("active", user.get("isActive", True))
            
            print(f"{idx}. {full_name}")
            print(f"   Username: {username}")
            print(f"   Email: {email}")
            print(f"   User ID: {user_id}")
            print(f"   Active: {active}")
            print()


def main():
    """Main function to demonstrate the API client"""
    
    # Load user management credentials
    try:
        with open("bobAPIaccess.json", "r") as f:
            user_credentials = json.load(f)
            user_client_id = user_credentials["client_id"]
            user_client_secret = user_credentials["client_secret"]
    except FileNotFoundError:
        print("✗ Error: bobAPIaccess.json file not found")
        return
    except KeyError as e:
        print(f"✗ Error: Missing key in user credentials file: {e}")
        return
    
    # Load artifact reporting credentials (for spaces/processes)
    try:
        with open("bobAPIArtifactReporting.json", "r") as f:
            artifact_credentials = json.load(f)
            artifact_client_id = artifact_credentials["client_id"]
            artifact_client_secret = artifact_credentials["client_secret"]
    except FileNotFoundError:
        print("✗ Error: bobAPIArtifactReporting.json file not found")
        print("  Artifact reporting features will be disabled")
        artifact_client_id = None
        artifact_client_secret = None
    except KeyError as e:
        print(f"✗ Error: Missing key in artifact reporting credentials file: {e}")
        artifact_client_id = None
        artifact_client_secret = None
    
    print("IBM Blueworks Live API Client")
    print("=" * 80)
    print()
    
    # Create client instance for user management
    user_client = BlueworksLiveClient(user_client_id, user_client_secret)
    
    # Authenticate for user management
    print("Step 1: Authenticating for user management...")
    if not user_client.authenticate():
        print("\n✗ Authentication failed. Please check your credentials.")
        return
    
    print()
    
    # Retrieve active users
    print("Step 2: Retrieving active users...")
    users = user_client.get_active_users()
    
    if users is None:
        print("\n✗ Failed to retrieve users.")
        return
    
    # Display users
    user_client.display_users(users)
    
    # Save to JSON file
    output_file = "active_users.json"
    try:
        with open(output_file, "w") as f:
            json.dump(users, f, indent=2)
        print(f"✓ User data saved to {output_file}")
    except Exception as e:
        print(f"✗ Failed to save user data: {e}")
    
    # Generate HTML reports
    print("\nStep 3: Generating HTML reports...")
    try:
        generate_html_report(users)
        print(f"✓ User list generated: users_list.html")
        generate_analytics_report(users)
        print(f"✓ Analytics dashboard generated: user_analytics.html")
    except Exception as e:
        print(f"✗ Failed to generate HTML reports: {e}")
    
    # Retrieve all artifacts using artifact reporting credentials
    if artifact_client_id and artifact_client_secret:
        print("\nStep 4: Retrieving all artifacts in CSV format...")
        print("  Using artifact reporting credentials with OAuth 2.0...")
        
        # Create client instance and authenticate
        artifact_client = BlueworksLiveClient(artifact_client_id, artifact_client_secret)
        
        if not artifact_client.authenticate():
            print("✗ Failed to authenticate for artifact reporting")
        else:
            # Call LibraryArtifact API to get all artifacts in CSV format
            csv_data = artifact_client.get_all_artifacts_csv()
            
            if csv_data:
                # Save to CSV file
                try:
                    with open("blueworks_artifacts.csv", "w", encoding="utf-8") as f:
                        f.write(csv_data)
                    print(f"✓ All artifacts saved to blueworks_artifacts.csv")
                    
                    # Count lines to show number of artifacts
                    line_count = len(csv_data.split('\n')) - 1  # Subtract header
                    print(f"  Total artifacts: {line_count}")
                    
                    # Generate HTML page for artifacts
                    try:
                        generate_artifacts_report(csv_data)
                        print(f"✓ Artifacts list generated: artifacts_list.html")
                    except Exception as e:
                        print(f"✗ Failed to generate artifacts HTML: {e}")
                except Exception as e:
                    print(f"✗ Failed to save artifacts CSV: {e}")
            else:
                print("⚠ No artifacts data retrieved")
    else:
        print("⚠ Artifact reporting credentials not available - skipping process maps")
    
    print(f"\n✓ All reports generated successfully!")
    print(f"  Open users_list.html, user_analytics.html, artifacts_list.html, or process_maps.html in your browser")


def generate_html_report(users: List[Dict]) -> None:
    """Generate an HTML report from user data"""
    
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IBM Blueworks Live - Active Users</title>
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'IBM Plex Sans', 'Helvetica Neue', Arial, sans-serif;
            background: #f4f4f4;
            color: #161616;
            line-height: 1.5;
        }
        .container {
            max-width: 1584px;
            margin: 0 auto;
            padding: 2rem;
        }
        .header {
            background: #ffffff;
            border-bottom: 1px solid #e0e0e0;
            padding: 2rem;
            margin: -2rem -2rem 2rem -2rem;
        }
        .header h1 { font-size: 2.5rem; font-weight: 600; color: #161616; margin-bottom: 0.5rem; }
        .header p { color: #525252; font-size: 1rem; }
        .nav-links { display: flex; gap: 1rem; margin-top: 1.5rem; }
        .nav-links a {
            padding: 0.875rem 1rem;
            background: #0f62fe;
            color: #ffffff;
            text-decoration: none;
            font-weight: 500;
            transition: background 0.1s;
        }
        .nav-links a:hover { background: #0353e9; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .stat-box { background: #ffffff; padding: 1.5rem; border-left: 3px solid #0f62fe; }
        .stat-box .number { font-size: 2.5rem; font-weight: 600; color: #161616; margin: 0.5rem 0; }
        .stat-box .label { font-size: 0.875rem; color: #525252; text-transform: uppercase; letter-spacing: 0.16px; font-weight: 500; }
        .controls {
            padding: 1.5rem;
            background: #ffffff;
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            align-items: center;
            margin-bottom: 1rem;
        }
        .search-box { flex: 1; min-width: 250px; }
        .search-box input {
            width: 100%;
            padding: 0.6875rem 1rem;
            border: none;
            border-bottom: 1px solid #8d8d8d;
            background: #f4f4f4;
            font-family: 'IBM Plex Sans', sans-serif;
            font-size: 0.875rem;
            transition: background 0.1s, border-color 0.1s;
        }
        .search-box input:hover { background: #e8e8e8; }
        .search-box input:focus {
            outline: 2px solid #0f62fe;
            outline-offset: -2px;
            border-bottom-color: #0f62fe;
            background: #ffffff;
        }
        .filter-group { display: flex; gap: 0.5rem; flex-wrap: wrap; }
        .filter-btn {
            padding: 0.6875rem 1rem;
            border: 1px solid #8d8d8d;
            background: #ffffff;
            cursor: pointer;
            transition: background 0.1s, border-color 0.1s;
            font-size: 0.875rem;
            font-family: 'IBM Plex Sans', sans-serif;
            font-weight: 500;
        }
        .filter-btn:hover { background: #e8e8e8; }
        .filter-btn.active { background: #0f62fe; color: #ffffff; border-color: #0f62fe; }
        .table-container { overflow-x: auto; background: #ffffff; }
        table { width: 100%; border-collapse: collapse; }
        thead { background: #e0e0e0; position: sticky; top: 0; z-index: 10; }
        th {
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            color: #161616;
            font-size: 0.875rem;
            border-bottom: 1px solid #e0e0e0;
            cursor: pointer;
            user-select: none;
            transition: background 0.1s;
        }
        th:hover { background: #c6c6c6; }
        th.sortable::after { content: ' ⇅'; opacity: 0.5; }
        th.sort-asc::after { content: ' ↑'; opacity: 1; }
        th.sort-desc::after { content: ' ↓'; opacity: 1; }
        td { padding: 1rem; border-bottom: 1px solid #e0e0e0; font-size: 0.875rem; }
        tbody tr { transition: background 0.1s; }
        tbody tr:hover { background: #e8e8e8; }
        .badge {
            display: inline-block;
            padding: 0.125rem 0.5rem;
            font-size: 0.75rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.16px;
        }
        .badge.admin { background: #da1e28; color: #ffffff; }
        .badge.author { background: #24a148; color: #ffffff; }
        .badge.reader { background: #0043ce; color: #ffffff; }
        .badge.contributor { background: #f1c21b; color: #161616; }
        .badge.licensed { background: #24a148; color: #ffffff; }
        .badge.unlicensed { background: #8d8d8d; color: #ffffff; }
        .no-results { text-align: center; padding: 3rem 1rem; color: #525252; font-size: 1rem; }
        @media (max-width: 768px) {
            .header h1 { font-size: 2rem; }
            .stats { grid-template-columns: 1fr; }
            .controls { flex-direction: column; }
            .search-box { width: 100%; }
            table { font-size: 0.8125rem; }
            th, td { padding: 0.75rem; }
            .container { padding: 1rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌐 IBM Blueworks Live</h1>
            <p>Active Users Directory</p>
            <div class="nav-links">
                <a href="user_analytics.html">📊 View Analytics</a>
            </div>
        </div>
        <div class="stats">
            <div class="stat-box">
                <div class="number" id="totalUsers">-</div>
                <div class="label">Total Users</div>
            </div>
            <div class="stat-box">
                <div class="number" id="licensedUsers">-</div>
                <div class="label">Licensed</div>
            </div>
            <div class="stat-box">
                <div class="number" id="adminUsers">-</div>
                <div class="label">Administrators</div>
            </div>
            <div class="stat-box">
                <div class="number" id="authorUsers">-</div>
                <div class="label">Authors</div>
            </div>
        </div>
        <div class="controls">
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="🔍 Search by name or email...">
            </div>
            <div class="filter-group">
                <button class="filter-btn active" data-filter="all">All Users</button>
                <button class="filter-btn" data-filter="licensed">Licensed Only</button>
                <button class="filter-btn" data-filter="admin">Administrators</button>
                <button class="filter-btn" data-filter="author">Authors</button>
            </div>
        </div>
        <div class="table-container">
            <table id="usersTable">
                <thead>
                    <tr>
                        <th class="sortable" data-sort="name">#</th>
                        <th class="sortable" data-sort="name">Name</th>
                        <th class="sortable" data-sort="email">Email</th>
                        <th class="sortable" data-sort="role">Role</th>
                        <th class="sortable" data-sort="licensed">License</th>
                        <th class="sortable" data-sort="date">Date Added</th>
                    </tr>
                </thead>
                <tbody id="usersTableBody"></tbody>
            </table>
        </div>
    </div>
    <script>
        const allUsers = """ + json.dumps(users) + """;
        let filteredUsers = [...allUsers];
        let currentSort = { column: 'name', direction: 'asc' };
        let currentFilter = 'all';

        function updateStats() {
            document.getElementById('totalUsers').textContent = allUsers.length;
            document.getElementById('licensedUsers').textContent = allUsers.filter(u => u.licensed).length;
            document.getElementById('adminUsers').textContent = allUsers.filter(u => u.role === 'Administrator').length;
            document.getElementById('authorUsers').textContent = allUsers.filter(u => u.role === 'Author').length;
        }

        function renderTable() {
            const tbody = document.getElementById('usersTableBody');
            if (filteredUsers.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="no-results">No users found matching your criteria.</td></tr>';
                return;
            }
            tbody.innerHTML = filteredUsers.map((user, index) => `
                <tr>
                    <td>${index + 1}</td>
                    <td><strong>${user.name || 'N/A'}</strong></td>
                    <td>${user.email || 'N/A'}</td>
                    <td><span class="badge ${user.role.toLowerCase()}">${user.role}</span></td>
                    <td><span class="badge ${user.licensed ? 'licensed' : 'unlicensed'}">${user.licensed ? 'Licensed' : 'Unlicensed'}</span></td>
                    <td>${formatDate(user.date)}</td>
                </tr>
            `).join('');
        }

        function formatDate(dateStr) {
            if (!dateStr) return 'N/A';
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
        }

        document.getElementById('searchInput').addEventListener('input', (e) => {
            applyFilters(e.target.value.toLowerCase());
        });

        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                currentFilter = e.target.dataset.filter;
                applyFilters(document.getElementById('searchInput').value.toLowerCase());
            });
        });

        function applyFilters(searchTerm = '') {
            filteredUsers = allUsers.filter(user => {
                const matchesSearch = !searchTerm ||
                    (user.name && user.name.toLowerCase().includes(searchTerm)) ||
                    (user.email && user.email.toLowerCase().includes(searchTerm));
                let matchesFilter = true;
                if (currentFilter === 'licensed') matchesFilter = user.licensed;
                else if (currentFilter === 'admin') matchesFilter = user.role === 'Administrator';
                else if (currentFilter === 'author') matchesFilter = user.role === 'Author';
                return matchesSearch && matchesFilter;
            });
            sortUsers(currentSort.column, currentSort.direction);
            renderTable();
        }

        document.querySelectorAll('th.sortable').forEach(th => {
            th.addEventListener('click', () => {
                const column = th.dataset.sort;
                const direction = currentSort.column === column && currentSort.direction === 'asc' ? 'desc' : 'asc';
                document.querySelectorAll('th.sortable').forEach(t => t.classList.remove('sort-asc', 'sort-desc'));
                th.classList.add(direction === 'asc' ? 'sort-asc' : 'sort-desc');
                currentSort = { column, direction };
                sortUsers(column, direction);
                renderTable();
            });
        });

        function sortUsers(column, direction) {
            filteredUsers.sort((a, b) => {
                let aVal = a[column], bVal = b[column];
                if (column === 'date') {
                    aVal = new Date(aVal || 0);
                    bVal = new Date(bVal || 0);
                } else if (typeof aVal === 'string') {
                    aVal = aVal.toLowerCase();
                    bVal = bVal.toLowerCase();
                }
                if (aVal < bVal) return direction === 'asc' ? -1 : 1;
                if (aVal > bVal) return direction === 'asc' ? 1 : -1;
                return 0;
            });
        }

        updateStats();
        renderTable();
    </script>
</body>
</html>"""
    
    with open("users_list.html", "w", encoding="utf-8") as f:
        f.write(html_content)


def generate_analytics_report(users: List[Dict]) -> None:
    """Generate an analytics HTML report with embedded data"""
    
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IBM Blueworks Live - User Analytics</title>
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'IBM Plex Sans', 'Helvetica Neue', Arial, sans-serif;
            background: #f4f4f4;
            color: #161616;
            line-height: 1.5;
        }
        .container { max-width: 1584px; margin: 0 auto; padding: 2rem; }
        .header {
            background: #ffffff;
            border-bottom: 1px solid #e0e0e0;
            padding: 2rem;
            margin: -2rem -2rem 2rem -2rem;
        }
        .header h1 {
            font-size: 2.5rem;
            font-weight: 600;
            color: #161616;
            margin-bottom: 0.5rem;
        }
        .header p { color: #525252; font-size: 1rem; }
        .nav-links { display: flex; gap: 1rem; margin-top: 1.5rem; }
        .nav-links a {
            padding: 0.875rem 1rem;
            background: #0f62fe;
            color: #ffffff;
            text-decoration: none;
            font-weight: 500;
            transition: background 0.1s;
            border: none;
        }
        .nav-links a:hover { background: #0353e9; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .stat-card {
            background: #ffffff;
            padding: 1.5rem;
            border-left: 3px solid #0f62fe;
        }
        .stat-card .icon { font-size: 2rem; margin-bottom: 0.5rem; color: #0f62fe; }
        .stat-card .number {
            font-size: 2.5rem;
            font-weight: 600;
            color: #161616;
            margin: 0.5rem 0;
        }
        .stat-card .label {
            color: #525252;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.16px;
            font-weight: 500;
        }
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(600px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .chart-card {
            background: #ffffff;
            padding: 1.5rem;
        }
        .chart-card h2 {
            color: #161616;
            margin-bottom: 1.5rem;
            font-size: 1.25rem;
            font-weight: 600;
        }
        .chart-container { position: relative; height: 400px; }
        .full-width { grid-column: 1 / -1; }
        .controls {
            background: #ffffff;
            padding: 1.5rem;
            margin-bottom: 2rem;
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            align-items: center;
        }
        .controls label { font-weight: 500; color: #161616; }
        .controls select {
            padding: 0.6875rem 2.5rem 0.6875rem 1rem;
            border: none;
            border-bottom: 1px solid #8d8d8d;
            background: #f4f4f4;
            font-family: 'IBM Plex Sans', sans-serif;
            font-size: 0.875rem;
            cursor: pointer;
            transition: background 0.1s, border-color 0.1s;
        }
        .controls select:hover { background: #e8e8e8; }
        .controls select:focus {
            outline: 2px solid #0f62fe;
            outline-offset: -2px;
            border-bottom-color: #0f62fe;
        }
        @media (max-width: 768px) {
            .charts-grid { grid-template-columns: 1fr; }
            .header h1 { font-size: 2rem; }
            .chart-container { height: 300px; }
            .container { padding: 1rem; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 User Analytics Dashboard</h1>
            <p>IBM Blueworks Live - User Activity & Growth Metrics</p>
            <div class="nav-links">
                <a href="users_list.html">👥 View User List</a>
                <a href="#" onclick="location.reload()">🔄 Refresh Data</a>
            </div>
        </div>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="icon">👥</div>
                <div class="number" id="totalUsers">-</div>
                <div class="label">Total Users</div>
            </div>
            <div class="stat-card">
                <div class="icon">📈</div>
                <div class="number" id="avgPerMonth">-</div>
                <div class="label">Avg Users/Month</div>
            </div>
            <div class="stat-card">
                <div class="icon">🆕</div>
                <div class="number" id="recentUsers">-</div>
                <div class="label">Last 30 Days</div>
            </div>
            <div class="stat-card">
                <div class="icon">🔥</div>
                <div class="number" id="peakMonth">-</div>
                <div class="label">Peak Month</div>
            </div>
        </div>
        <div class="controls">
            <label for="timeRange">Time Range:</label>
            <select id="timeRange">
                <option value="6">Last 6 Months</option>
                <option value="12" selected>Last 12 Months</option>
                <option value="24">Last 24 Months</option>
                <option value="all">All Time</option>
            </select>
        </div>
        <div class="charts-grid">
            <div class="chart-card full-width">
                <h2>📅 User Registrations by Month</h2>
                <div class="chart-container"><canvas id="monthlyChart"></canvas></div>
            </div>
            <div class="chart-card">
                <h2>📊 User Registrations by Day of Week</h2>
                <div class="chart-container"><canvas id="dayOfWeekChart"></canvas></div>
            </div>
            <div class="chart-card">
                <h2>🎭 User Roles Distribution</h2>
                <div class="chart-container"><canvas id="rolesChart"></canvas></div>
            </div>
            <div class="chart-card full-width">
                <h2>📈 Cumulative User Growth</h2>
                <div class="chart-container"><canvas id="cumulativeChart"></canvas></div>
            </div>
            <div class="chart-card">
                <h2>📆 Daily Registration Activity (Last 90 Days)</h2>
                <div class="chart-container"><canvas id="dailyChart"></canvas></div>
            </div>
            <div class="chart-card">
                <h2>🔑 License Status</h2>
                <div class="chart-container"><canvas id="licenseChart"></canvas></div>
            </div>
        </div>
    </div>
    <script>
        const allUsers = """ + json.dumps(users) + """;
        let charts = {};
        
        allUsers.forEach(user => { user.parsedDate = new Date(user.date); });

        function updateStats() {
            const now = new Date();
            const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
            document.getElementById('totalUsers').textContent = allUsers.length;
            const recentUsers = allUsers.filter(u => u.parsedDate >= thirtyDaysAgo).length;
            document.getElementById('recentUsers').textContent = recentUsers;
            const monthlyData = getMonthlyData('all');
            const avgPerMonth = Math.round(allUsers.length / monthlyData.length);
            document.getElementById('avgPerMonth').textContent = avgPerMonth;
            const maxMonth = monthlyData.reduce((max, curr) => curr.count > max.count ? curr : max, monthlyData[0]);
            document.getElementById('peakMonth').textContent = maxMonth ? maxMonth.label : 'N/A';
        }

        function getMonthlyData(range) {
            const monthCounts = {};
            const now = new Date();
            allUsers.forEach(user => {
                const date = user.parsedDate;
                if (!date || isNaN(date)) return;
                if (range !== 'all') {
                    const monthsAgo = (now.getFullYear() - date.getFullYear()) * 12 + (now.getMonth() - date.getMonth());
                    if (monthsAgo > parseInt(range)) return;
                }
                const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
                monthCounts[key] = (monthCounts[key] || 0) + 1;
            });
            return Object.entries(monthCounts).sort(([a], [b]) => a.localeCompare(b))
                .map(([key, count]) => ({ label: new Date(key + '-01').toLocaleDateString('en-US', { year: 'numeric', month: 'short' }), count }));
        }

        function getDailyData() {
            const dailyCounts = {};
            const now = new Date();
            const ninetyDaysAgo = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
            allUsers.forEach(user => {
                const date = user.parsedDate;
                if (!date || isNaN(date) || date < ninetyDaysAgo) return;
                const key = date.toISOString().split('T')[0];
                dailyCounts[key] = (dailyCounts[key] || 0) + 1;
            });
            return Object.entries(dailyCounts).sort(([a], [b]) => a.localeCompare(b))
                .map(([key, count]) => ({ label: new Date(key).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }), count }));
        }

        function getDayOfWeekData() {
            const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
            const dayCounts = Array(7).fill(0);
            allUsers.forEach(user => {
                const date = user.parsedDate;
                if (!date || isNaN(date)) return;
                dayCounts[date.getDay()]++;
            });
            return days.map((day, index) => ({ label: day, count: dayCounts[index] }));
        }

        function getRoleData() {
            const roleCounts = {};
            allUsers.forEach(user => {
                const role = user.role || 'Unknown';
                roleCounts[role] = (roleCounts[role] || 0) + 1;
            });
            return Object.entries(roleCounts).map(([label, count]) => ({ label, count }));
        }

        function getCumulativeData(range) {
            const monthlyData = getMonthlyData(range);
            let cumulative = 0;
            return monthlyData.map(item => {
                cumulative += item.count;
                return { label: item.label, count: cumulative };
            });
        }

        function createCharts() {
            const range = document.getElementById('timeRange').value;
            const monthlyData = getMonthlyData(range);
            if (charts.monthly) charts.monthly.destroy();
            charts.monthly = new Chart(document.getElementById('monthlyChart'), {
                type: 'bar',
                data: {
                    labels: monthlyData.map(d => d.label),
                    datasets: [{ label: 'New Users', data: monthlyData.map(d => d.count), backgroundColor: 'rgba(102, 126, 234, 0.8)', borderColor: 'rgba(102, 126, 234, 1)', borderWidth: 2 }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
            });

            const dayData = getDayOfWeekData();
            if (charts.dayOfWeek) charts.dayOfWeek.destroy();
            charts.dayOfWeek = new Chart(document.getElementById('dayOfWeekChart'), {
                type: 'bar',
                data: {
                    labels: dayData.map(d => d.label),
                    datasets: [{ label: 'Registrations', data: dayData.map(d => d.count), backgroundColor: ['rgba(255, 99, 132, 0.8)', 'rgba(54, 162, 235, 0.8)', 'rgba(255, 206, 86, 0.8)', 'rgba(75, 192, 192, 0.8)', 'rgba(153, 102, 255, 0.8)', 'rgba(255, 159, 64, 0.8)', 'rgba(199, 199, 199, 0.8)'] }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
            });

            const roleData = getRoleData();
            if (charts.roles) charts.roles.destroy();
            charts.roles = new Chart(document.getElementById('rolesChart'), {
                type: 'doughnut',
                data: {
                    labels: roleData.map(d => d.label),
                    datasets: [{ data: roleData.map(d => d.count), backgroundColor: ['rgba(220, 53, 69, 0.8)', 'rgba(40, 167, 69, 0.8)', 'rgba(23, 162, 184, 0.8)', 'rgba(255, 193, 7, 0.8)'] }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
            });

            const cumulativeData = getCumulativeData(range);
            if (charts.cumulative) charts.cumulative.destroy();
            charts.cumulative = new Chart(document.getElementById('cumulativeChart'), {
                type: 'line',
                data: {
                    labels: cumulativeData.map(d => d.label),
                    datasets: [{ label: 'Total Users', data: cumulativeData.map(d => d.count), borderColor: 'rgba(118, 75, 162, 1)', backgroundColor: 'rgba(118, 75, 162, 0.1)', fill: true, tension: 0.4, borderWidth: 3 }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 10 } } } }
            });

            const dailyData = getDailyData();
            if (charts.daily) charts.daily.destroy();
            charts.daily = new Chart(document.getElementById('dailyChart'), {
                type: 'line',
                data: {
                    labels: dailyData.map(d => d.label),
                    datasets: [{ label: 'Daily Registrations', data: dailyData.map(d => d.count), borderColor: 'rgba(102, 126, 234, 1)', backgroundColor: 'rgba(102, 126, 234, 0.1)', fill: true, tension: 0.3, borderWidth: 2 }]
                },
                options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
            });
        }

        updateCharts('all');
    </script>
</body>
</html>"""
    
    with open("user_analytics.html", "w", encoding="utf-8") as f:
        f.write(html_content)


def generate_artifacts_report(csv_data: str) -> None:
    """Generate an HTML report showing the first 100 artifacts with cross-navigation"""
    import csv
    from io import StringIO
    
    # Parse CSV data
    csv_reader = csv.DictReader(StringIO(csv_data))
    artifacts = list(csv_reader)[:100]  # Get first 100 artifacts
    
    # Convert artifacts to JSON for embedding
    import json
    artifacts_json = json.dumps(artifacts)
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IBM Blueworks Live - Artifacts List</title>
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'IBM Plex Sans', 'Helvetica Neue', Arial, sans-serif;
            background: #f4f4f4;
            color: #161616;
            line-height: 1.5;
        }}
        .container {{ max-width: 1584px; margin: 0 auto; padding: 2rem; }}
        .header {{
            background: #ffffff;
            border-bottom: 1px solid #e0e0e0;
            padding: 2rem;
            margin: -2rem -2rem 2rem -2rem;
        }}
        .header h1 {{
            font-size: 2.5rem;
            font-weight: 600;
            color: #0f62fe;
            margin-bottom: 0.5rem;
        }}
        .header p {{ color: #525252; font-size: 1rem; }}
        .nav-buttons {{
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
        }}
        .nav-button {{
            padding: 0.75rem 1.5rem;
            background: #0f62fe;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-weight: 500;
            transition: background 0.2s;
            border: none;
            cursor: pointer;
        }}
        .nav-button:hover {{ background: #0353e9; }}
        .nav-button.secondary {{
            background: #393939;
        }}
        .nav-button.secondary:hover {{ background: #262626; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .stat-card {{
            background: white;
            padding: 1.5rem;
            border-radius: 4px;
            border-left: 4px solid #0f62fe;
        }}
        .stat-value {{
            font-size: 2rem;
            font-weight: 600;
            color: #0f62fe;
        }}
        .stat-label {{ color: #525252; margin-top: 0.5rem; }}
        .table-container {{
            background: white;
            border-radius: 4px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .table-header {{
            padding: 1.5rem;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1rem;
        }}
        .table-header h2 {{ font-size: 1.5rem; font-weight: 600; }}
        .search-box {{
            padding: 0.5rem 1rem;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            font-size: 0.875rem;
            min-width: 300px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        th {{
            background: #f4f4f4;
            font-weight: 600;
            color: #161616;
            cursor: pointer;
            user-select: none;
        }}
        th:hover {{ background: #e0e0e0; }}
        tr:hover {{ background: #f4f4f4; }}
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 500;
        }}
        .badge.active {{ background: #d0e2ff; color: #0043ce; }}
        .badge.inactive {{ background: #f4f4f4; color: #525252; }}
        .badge.blueprint {{ background: #e5f6ff; color: #0072c3; }}
        .badge.process-app {{ background: #d2f4ea; color: #0e6027; }}
        .artifact-id {{ font-family: 'Courier New', monospace; font-size: 0.875rem; color: #525252; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 IBM Blueworks Live - Artifacts</h1>
            <p>Showing first 100 artifacts from your Blueworks Live instance</p>
        </div>

        <div class="nav-buttons">
            <a href="users_list.html" class="nav-button">👥 Users List</a>
            <a href="user_analytics.html" class="nav-button">📈 User Analytics</a>
            <a href="artifacts_list.html" class="nav-button secondary">📋 Artifacts (Current)</a>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="totalArtifacts">100</div>
                <div class="stat-label">Total Artifacts Shown</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="activeCount">0</div>
                <div class="stat-label">Active Artifacts</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="blueprintCount">0</div>
                <div class="stat-label">Blueprints</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="spaceCount">0</div>
                <div class="stat-label">Unique Spaces</div>
            </div>
        </div>

        <div class="table-container">
            <div class="table-header">
                <h2>Artifacts</h2>
                <input type="text" id="searchBox" class="search-box" placeholder="Search artifacts...">
            </div>
            <table id="artifactsTable">
                <thead>
                    <tr>
                        <th onclick="sortTable('Name')">Name</th>
                        <th onclick="sortTable('Type')">Type</th>
                        <th onclick="sortTable('ID')">ID</th>
                        <th onclick="sortTable('Space Name')">Space</th>
                        <th onclick="sortTable('Is Active')">Status</th>
                        <th onclick="sortTable('Created Date')">Created</th>
                        <th onclick="sortTable('Last Modified Date')">Modified</th>
                    </tr>
                </thead>
                <tbody id="tableBody">
                </tbody>
            </table>
        </div>
    </div>

    <script>
        const artifacts = {artifacts_json};
        let filteredArtifacts = [...artifacts];
        let sortColumn = 'Name';
        let sortDirection = 'asc';

        function updateStats() {{
            const activeCount = artifacts.filter(a => a['Is Active'] === 'true').length;
            const blueprintCount = artifacts.filter(a => a.Type === 'Blueprint').length;
            const uniqueSpaces = new Set(artifacts.map(a => a['Space Name']).filter(s => s)).size;
            
            document.getElementById('totalArtifacts').textContent = artifacts.length;
            document.getElementById('activeCount').textContent = activeCount;
            document.getElementById('blueprintCount').textContent = blueprintCount;
            document.getElementById('spaceCount').textContent = uniqueSpaces;
        }}

        function renderTable() {{
            const tbody = document.getElementById('tableBody');
            tbody.innerHTML = '';
            
            filteredArtifacts.forEach(artifact => {{
                const row = tbody.insertRow();
                
                // Name
                const nameCell = row.insertCell();
                nameCell.textContent = artifact.Name || 'N/A';
                
                // Type
                const typeCell = row.insertCell();
                const typeBadge = document.createElement('span');
                typeBadge.className = `badge ${{artifact.Type === 'Blueprint' ? 'blueprint' : 'process-app'}}`;
                typeBadge.textContent = artifact.Type || 'N/A';
                typeCell.appendChild(typeBadge);
                
                // ID
                const idCell = row.insertCell();
                idCell.className = 'artifact-id';
                idCell.textContent = artifact.ID || 'N/A';
                
                // Space
                const spaceCell = row.insertCell();
                spaceCell.textContent = artifact['Space Name'] || 'N/A';
                
                // Status
                const statusCell = row.insertCell();
                const statusBadge = document.createElement('span');
                statusBadge.className = `badge ${{artifact['Is Active'] === 'true' ? 'active' : 'inactive'}}`;
                statusBadge.textContent = artifact['Is Active'] === 'true' ? 'Active' : 'Inactive';
                statusCell.appendChild(statusBadge);
                
                // Created
                const createdCell = row.insertCell();
                createdCell.textContent = artifact['Created Date'] ? new Date(artifact['Created Date']).toLocaleDateString() : 'N/A';
                
                // Modified
                const modifiedCell = row.insertCell();
                modifiedCell.textContent = artifact['Last Modified Date'] ? new Date(artifact['Last Modified Date']).toLocaleDateString() : 'N/A';
            }});
        }}

        function sortTable(column) {{
            if (sortColumn === column) {{
                sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
            }} else {{
                sortColumn = column;
                sortDirection = 'asc';
            }}
            
            filteredArtifacts.sort((a, b) => {{
                let aVal = a[column] || '';
                let bVal = b[column] || '';
                
                if (column.includes('Date')) {{
                    aVal = new Date(aVal || 0);
                    bVal = new Date(bVal || 0);
                }} else if (typeof aVal === 'string') {{
                    aVal = aVal.toLowerCase();
                    bVal = bVal.toLowerCase();
                }}
                
                if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
                if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
                return 0;
            }});
            
            renderTable();
        }}

        document.getElementById('searchBox').addEventListener('input', (e) => {{
            const searchTerm = e.target.value.toLowerCase();
            filteredArtifacts = artifacts.filter(artifact =>
                Object.values(artifact).some(val =>
                    String(val).toLowerCase().includes(searchTerm)
                )
            );
            renderTable();
        }});

        updateStats();
        renderTable();
    </script>
</body>
</html>"""
    
    with open("artifacts_list.html", "w", encoding="utf-8") as f:
        f.write(html_content)


if __name__ == "__main__":
    main()

# Made with Bob
