import requests
import urllib.parse
import os
import fnmatch
from typing import Any, List, Optional
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class Obsidian():
    def __init__(
            self, 
            api_key: str,
            protocol: str = os.getenv('OBSIDIAN_PROTOCOL', 'https'),
            host: str = os.getenv('OBSIDIAN_HOST', '127.0.0.1'),
            port: int = int(os.getenv('OBSIDIAN_PORT', '27124')),
            verify_ssl: bool = False,
            whitelist: Optional[List[str]] = None,
        ):
        self.api_key = api_key
        
        protocol = protocol.lower()
        if protocol == 'http':
            self.protocol = 'http'
        else:
            self.protocol = 'https' # Default to https for any other value, including 'https'

        self.host = host
        self.port = port
        self.verify_ssl = verify_ssl
        self.timeout = (10, 30)  # Increased timeout for initial connections
        
        # Initialize whitelist - if None, load from environment
        if whitelist is None:
            whitelist_env = os.getenv('OBSIDIAN_WHITELIST', '')
            if whitelist_env:
                self.whitelist = [path.strip() for path in whitelist_env.split(',') if path.strip()]
            else:
                self.whitelist = []
        else:
            self.whitelist = whitelist
        
        # If whitelist is empty, allow all paths (backward compatibility)
        self.whitelist_enabled = len(self.whitelist) > 0

    def get_base_url(self) -> str:
        return f'{self.protocol}://{self.host}:{self.port}'
    
    def _get_headers(self) -> dict:
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }
        return headers

    def _safe_call(self, f) -> Any:
        try:
            return f()
        except requests.HTTPError as e:
            error_data = e.response.json() if e.response.content else {}
            code = error_data.get('errorCode', -1) 
            message = error_data.get('message', '<unknown>')
            raise Exception(f"Error {code}: {message}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")

    def list_files_in_vault(self) -> Any:
        url = f"{self.get_base_url()}/vault/"
        
        def call_fn():
            response = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            
            files = response.json()['files']
            # Filter files based on whitelist
            return self._filter_files_by_whitelist(files)

        return self._safe_call(call_fn)

        
    def list_files_in_dir(self, dirpath: str) -> Any:
        # Validate directory access
        self._validate_path_access(dirpath)
        
        url = f"{self.get_base_url()}/vault/{dirpath}/"
        
        def call_fn():
            response = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            
            files = response.json()['files']
            # Filter files based on whitelist (prepend dirpath to each file for checking)
            filtered_files = []
            for file in files:
                full_path = f"{dirpath}/{file}" if dirpath else file
                if self._is_path_allowed(full_path):
                    filtered_files.append(file)
            return filtered_files

        return self._safe_call(call_fn)

    def get_file_contents(self, filepath: str) -> Any:
        # Validate file access
        self._validate_path_access(filepath)
        
        url = f"{self.get_base_url()}/vault/{filepath}"
    
        def call_fn():
            response = requests.get(url, headers=self._get_headers(), verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            
            return response.text

        return self._safe_call(call_fn)
    
    def get_batch_file_contents(self, filepaths: list[str]) -> str:
        """Get contents of multiple files and concatenate them with headers.
        
        Args:
            filepaths: List of file paths to read
            
        Returns:
            String containing all file contents with headers
        """
        import time
        
        result = []
        
        # Use a session for connection reuse
        with requests.Session() as session:
            session.headers.update(self._get_headers())
            session.verify = self.verify_ssl
            
            for i, filepath in enumerate(filepaths):
                try:
                    # Validate file access before attempting to read
                    self._validate_path_access(filepath)
                    
                    # Add small delay between requests (except for first one)
                    if i > 0:
                        time.sleep(0.1)  # 100ms delay
                    
                    # Make HTTP request using session
                    url = f"{self.get_base_url()}/vault/{filepath}"
                    
                    def call_fn():
                        response = session.get(url, timeout=self.timeout)
                        response.raise_for_status()
                        return response.text
                    
                    content = self._safe_call(call_fn)
                    result.append(f"# {filepath}\n\n{content}\n\n---\n\n")
                except PermissionError as e:
                    # Add permission error message but continue processing other files
                    result.append(f"# {filepath}\n\n{str(e)}\n\n---\n\n")
                except Exception as e:
                    # Add error message but continue processing other files
                    result.append(f"# {filepath}\n\nError reading file: {str(e)}\n\n---\n\n")
                
        return "".join(result)

    def search(self, query: str, context_length: int = 100) -> Any:
        url = f"{self.get_base_url()}/search/simple/"
        params = {
            'query': query,
            'contextLength': context_length
        }
        
        def call_fn():
            response = requests.post(url, headers=self._get_headers(), params=params, verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            results = response.json()
            
            # Filter results based on whitelist
            if self.whitelist_enabled:
                filtered_results = []
                for result in results:
                    filename = result.get('filename', '')
                    if self._is_path_allowed(filename):
                        filtered_results.append(result)
                return filtered_results
            
            return results

        return self._safe_call(call_fn)
    
    def search_json(self, query: dict) -> Any:
        url = f"{self.get_base_url()}/search/"
        
        headers = self._get_headers() | {
            'Content-Type': 'application/vnd.olrapi.jsonlogic+json'
        }
        
        def call_fn():
            response = requests.post(url, headers=headers, json=query, verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            results = response.json()
            
            # Filter results based on whitelist
            if self.whitelist_enabled:
                filtered_results = []
                for result in results:
                    # The result structure might vary, but typically has a 'path' field
                    path = result.get('path', result.get('filename', ''))
                    if self._is_path_allowed(path):
                        filtered_results.append(result)
                return filtered_results
            
            return results

        return self._safe_call(call_fn)
    
    def get_periodic_note(self, period: str, type: str = "content") -> Any:
        """Get current periodic note for the specified period.
        
        Args:
            period: The period type (daily, weekly, monthly, quarterly, yearly)
            type: Type of the data to get ('content' or 'metadata'). 
                'content' returns just the content in Markdown format. 
                'metadata' includes note metadata (including paths, tags, etc.) and the content.. 
            
        Returns:
            Content of the periodic note
        """
        url = f"{self.get_base_url()}/periodic/{period}/"
        
        def call_fn():
            headers = self._get_headers()
            if type == "metadata":
                headers['Accept'] = 'application/vnd.olrapi.note+json'
            response = requests.get(url, headers=headers, verify=self.verify_ssl, timeout=self.timeout)
            response.raise_for_status()
            
            return response.text

        return self._safe_call(call_fn)
    
    def get_recent_periodic_notes(self, period: str, limit: int = 5, include_content: bool = False) -> Any:
        """Get most recent periodic notes for the specified period type.
        
        Args:
            period: The period type (daily, weekly, monthly, quarterly, yearly)
            limit: Maximum number of notes to return (default: 5)
            include_content: Whether to include note content (default: False)
            
        Returns:
            List of recent periodic notes
        """
        url = f"{self.get_base_url()}/periodic/{period}/recent"
        params = {
            "limit": limit,
            "includeContent": include_content
        }
        
        def call_fn():
            response = requests.get(
                url, 
                headers=self._get_headers(), 
                params=params,
                verify=self.verify_ssl, 
                timeout=self.timeout
            )
            response.raise_for_status()
            
            return response.json()

        return self._safe_call(call_fn)
    
    def get_recent_changes(self, limit: int = 10, days: int = 90) -> Any:
        """Get recently modified files in the vault.
        
        Args:
            limit: Maximum number of files to return (default: 10)
            days: Only include files modified within this many days (default: 90)
            
        Returns:
            List of recently modified files with metadata
        """
        # Build the DQL query
        query_lines = [
            "TABLE file.mtime",
            f"WHERE file.mtime >= date(today) - dur({days} days)",
            "SORT file.mtime DESC",
            f"LIMIT {limit}"
        ]
        
        # Join with proper DQL line breaks
        dql_query = "\n".join(query_lines)
        
        # Make the request to search endpoint
        url = f"{self.get_base_url()}/search/"
        headers = self._get_headers() | {
            'Content-Type': 'application/vnd.olrapi.dataview.dql+txt'
        }
        
        def call_fn():
            response = requests.post(
                url,
                headers=headers,
                data=dql_query.encode('utf-8'),
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        return self._safe_call(call_fn)

    def get_all_tags(self) -> Any:
        """Get all unique tags used in the vault.
        
        Returns:
            List of unique tags used across all notes in the vault
        """
        # Build the Dataview DQL query
        dql_query = """TABLE file.tags
WHERE file.tags"""
        
        # Make the request to search endpoint
        url = f"{self.get_base_url()}/search/"
        headers = self._get_headers() | {
            'Content-Type': 'application/vnd.olrapi.dataview.dql+txt'
        }
        
        def call_fn():
            response = requests.post(
                url,
                headers=headers,
                data=dql_query.encode('utf-8'),
                verify=self.verify_ssl,
                timeout=self.timeout
            )
            response.raise_for_status()
            results = response.json()
            
            # Extract and flatten tags from the Dataview results
            all_tags = set()
            for result in results:
                file_tags = result.get('result', {}).get('file.tags')
                if file_tags and isinstance(file_tags, list):
                    for tag in file_tags:
                        if tag:  # Skip empty tags
                            all_tags.add(tag)
            
            # Convert to sorted list for consistent output
            return sorted(list(all_tags))

        return self._safe_call(call_fn)

    def _is_path_allowed(self, path: str) -> bool:
        """Check if a path is allowed based on the whitelist configuration.
        
        Args:
            path: The file or directory path to check
            
        Returns:
            True if the path is allowed, False otherwise
        """
        if not self.whitelist_enabled:
            return True
        
        # Normalize the path (remove leading/trailing slashes)
        normalized_path = path.strip('/')
        
        # Check against each whitelist pattern
        for pattern in self.whitelist:
            # Normalize the pattern
            normalized_pattern = pattern.strip('/')
            
            # Check if the path matches the pattern exactly
            if normalized_path == normalized_pattern:
                return True
            
            # Check if the path starts with the pattern (for directory matching)
            if normalized_path.startswith(normalized_pattern + '/'):
                return True
            
            # Check if the pattern matches using glob-style matching
            if fnmatch.fnmatch(normalized_path, normalized_pattern):
                return True
        
        return False
    
    def _validate_path_access(self, path: str) -> None:
        """Validate that a path is allowed according to the whitelist.
        
        Args:
            path: The file or directory path to validate
            
        Raises:
            PermissionError: If the path is not allowed by the whitelist
        """
        if not self._is_path_allowed(path):
            raise PermissionError(f"Access denied: Path '{path}' is not in the whitelist")
    
    def _filter_files_by_whitelist(self, files: List[str]) -> List[str]:
        """Filter a list of files based on the whitelist configuration.
        
        Args:
            files: List of file paths to filter
            
        Returns:
            Filtered list of files that are allowed by the whitelist
        """
        if not self.whitelist_enabled:
            return files
        
        return [file for file in files if self._is_path_allowed(file)]
