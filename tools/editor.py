import os
from pathlib import Path
from typing import List, Literal, Optional, Union

from .base import BaseAnthropicTool, ToolError, ToolResult

class EditorTool(BaseAnthropicTool):
    """
    A file editor tool that allows Claude to view, create, and edit files.
    """
    
    name = "str_replace_editor"
    api_type = "text_editor_20250124"
    
    _file_history = {}  # Dict to store file history for undo operations
    
    def to_params(self) -> dict:
        """Returns the tool parameters for the Anthropic API."""
        return {
            "type": self.api_type,
            "name": self.name,
        }
    
    async def __call__(
        self,
        *,
        command: Literal["view", "create", "str_replace", "insert", "undo_edit"],
        path: str,
        file_text: Optional[str] = None,
        view_range: Optional[List[int]] = None,
        old_str: Optional[str] = None,
        new_str: Optional[str] = None,
        insert_line: Optional[int] = None,
        **kwargs
    ) -> ToolResult:
        """Execute file editing operations."""
        _path = Path(path)
        try:
            # Validate the path/command combination
            self._validate_path(command, _path)
            
            if command == "view":
                return await self._view(_path, view_range)
                
            elif command == "create":
                if file_text is None:
                    raise ToolError("Parameter 'file_text' is required for the 'create' command")
                return self._create(_path, file_text)
                
            elif command == "str_replace":
                if old_str is None:
                    raise ToolError("Parameter 'old_str' is required for the 'str_replace' command")
                return self._str_replace(_path, old_str, new_str or "")
                
            elif command == "insert":
                if insert_line is None:
                    raise ToolError("Parameter 'insert_line' is required for the 'insert' command")
                if new_str is None:
                    raise ToolError("Parameter 'new_str' is required for the 'insert' command")
                return self._insert(_path, insert_line, new_str)
                
            elif command == "undo_edit":
                return self._undo_edit(_path)
                
            else:
                raise ToolError(f"Unrecognized command: {command}")
        
        except ToolError as e:
            return ToolResult(error=e.message)
        except Exception as e:
            return ToolResult(error=f"An error occurred: {str(e)}")
    
    def _validate_path(self, command: str, path: Path) -> None:
        """Validate the path for the specified command."""
        # Check if it's an absolute path
        if not path.is_absolute():
            suggested_path = Path(os.getcwd()) / path
            raise ToolError(
                f"The path {path} is not an absolute path. Did you mean {suggested_path}?"
            )
            
        # Check if path exists (except for create command)
        if not path.exists() and command != "create":
            raise ToolError(f"The path {path} does not exist")
            
        # Check if path already exists for create command
        if path.exists() and command == "create":
            raise ToolError(f"File already exists at {path}")
            
        # Check if path is a directory (only view command can be used on directories)
        if path.is_dir() and command != "view":
            raise ToolError(f"The path {path} is a directory. Only the 'view' command can be used on directories")
    
    async def _view(self, path: Path, view_range: Optional[List[int]] = None) -> ToolResult:
        """Implement the view command."""
        if path.is_dir():
            if view_range:
                raise ToolError("The 'view_range' parameter cannot be used when viewing a directory")
                
            try:
                files = list(path.glob('*'))
                output = f"Contents of directory {path}:\n\n"
                output += "\n".join(f"{i+1}. {f.name}" for i, f in enumerate(files))
                return ToolResult(output=output)
            except Exception as e:
                raise ToolError(f"Failed to list directory contents: {str(e)}")
        
        # Read file content
        file_content = self._read_file(path)
        
        # Apply view range if provided
        if view_range:
            if len(view_range) != 2 or not all(isinstance(i, int) for i in view_range):
                raise ToolError("Invalid 'view_range'. It should be a list of two integers")
                
            lines = file_content.split('\n')
            line_count = len(lines)
            
            start, end = view_range
            if start < 1 or start > line_count:
                raise ToolError(f"Invalid 'view_range': Start line {start} is out of range (1-{line_count})")
                
            if end != -1 and (end < start or end > line_count):
                raise ToolError(f"Invalid 'view_range': End line {end} is out of range ({start}-{line_count})")
                
            if end == -1:
                lines = lines[start-1:]
            else:
                lines = lines[start-1:end]
                
            file_content = '\n'.join(lines)
            
            # Create line numbers
            numbered_content = '\n'.join([f"{i+start:4d} | {line}" for i, line in enumerate(lines)])
            output = f"File: {path} (lines {start}-{end if end != -1 else line_count}):\n\n{numbered_content}"
            
        else:
            # Create line numbers for all lines
            lines = file_content.split('\n')
            numbered_content = '\n'.join([f"{i+1:4d} | {line}" for i, line in enumerate(lines)])
            output = f"File: {path}:\n\n{numbered_content}"
            
        return ToolResult(output=output)
    
    def _create(self, path: Path, file_text: str) -> ToolResult:
        """Implement the create command."""
        try:
            # Create parent directory if it doesn't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file content
            self._write_file(path, file_text)
            
            return ToolResult(output=f"File created successfully at: {path}")
        except Exception as e:
            raise ToolError(f"Failed to create file: {str(e)}")
    
    def _str_replace(self, path: Path, old_str: str, new_str: str) -> ToolResult:
        """Implement the str_replace command."""
        # Read file content
        file_content = self._read_file(path)
        
        # Check if old_str exists in the file
        occurrences = file_content.count(old_str)
        if occurrences == 0:
            raise ToolError(f"No replacements made: '{old_str}' not found in {path}")
            
        if occurrences > 1:
            # Find line numbers of occurrences
            lines = file_content.split('\n')
            occurrences_lines = [i+1 for i, line in enumerate(lines) if old_str in line]
            raise ToolError(f"Multiple occurrences of '{old_str}' found in lines {occurrences_lines}. Please make sure it is unique.")
            
        # Save to history before making changes
        if path not in self._file_history:
            self._file_history[path] = []
        self._file_history[path].append(file_content)
        
        # Replace old_str with new_str
        new_content = file_content.replace(old_str, new_str)
        
        # Write updated content
        self._write_file(path, new_content)
        
        # Find the line number of the replacement for better feedback
        line_num = file_content.split(old_str)[0].count('\n') + 1
        
        # Create a snippet of the changed area
        context_lines = 3  # Show 3 lines before and after the change
        lines = new_content.split('\n')
        start_line = max(0, line_num - context_lines - 1)
        end_line = min(len(lines), line_num + context_lines)
        
        snippet_lines = [f"{i+1:4d} | {line}" for i, line in enumerate(lines[start_line:end_line])]
        snippet = '\n'.join(snippet_lines)
        
        output = f"File {path} has been edited. Here's a snippet of the result:\n\n{snippet}"
        return ToolResult(output=output)
    
    def _insert(self, path: Path, insert_line: int, new_str: str) -> ToolResult:
        """Implement the insert command."""
        # Read file content
        file_content = self._read_file(path)
        lines = file_content.split('\n')
        
        # Check if insert_line is valid
        if insert_line < 0 or insert_line > len(lines):
            raise ToolError(f"Invalid 'insert_line' parameter: {insert_line}. Should be between 0 and {len(lines)}")
            
        # Save to history before making changes
        if path not in self._file_history:
            self._file_history[path] = []
        self._file_history[path].append(file_content)
        
        # Insert the new string
        new_lines = new_str.split('\n')
        result_lines = lines[:insert_line] + new_lines + lines[insert_line:]
        new_content = '\n'.join(result_lines)
        
        # Write updated content
        self._write_file(path, new_content)
        
        # Create a snippet of the changed area
        context_lines = 3  # Show 3 lines before and after the change
        start_line = max(0, insert_line - context_lines)
        end_line = min(len(result_lines), insert_line + len(new_lines) + context_lines)
        
        snippet_lines = [f"{i+1:4d} | {line}" for i, line in enumerate(result_lines[start_line:end_line])]
        snippet = '\n'.join(snippet_lines)
        
        output = f"File {path} has been edited. Here's a snippet of the result:\n\n{snippet}"
        return ToolResult(output=output)
    
    def _undo_edit(self, path: Path) -> ToolResult:
        """Implement the undo_edit command."""
        if path not in self._file_history or not self._file_history[path]:
            raise ToolError(f"No edit history found for {path}")
            
        # Get the last version and restore it
        previous_content = self._file_history[path].pop()
        self._write_file(path, previous_content)
        
        lines = previous_content.split('\n')
        snippet_lines = [f"{i+1:4d} | {line}" for i, line in enumerate(lines[:10])]  # Show first 10 lines
        snippet = '\n'.join(snippet_lines)
        
        if len(lines) > 10:
            snippet += "\n... (file continues)"
            
        output = f"Last edit to {path} undone successfully. Here's a preview:\n\n{snippet}"
        return ToolResult(output=output)
    
    def _read_file(self, path: Path) -> str:
        """Read the content of a file."""
        try:
            return path.read_text(encoding='utf-8')
        except Exception as e:
            raise ToolError(f"Failed to read file {path}: {str(e)}")
    
    def _write_file(self, path: Path, content: str) -> None:
        """Write content to a file."""
        try:
            path.write_text(content, encoding='utf-8')
        except Exception as e:
            raise ToolError(f"Failed to write to file {path}: {str(e)}")