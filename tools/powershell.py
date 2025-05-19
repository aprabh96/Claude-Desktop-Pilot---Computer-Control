import asyncio
import os
import subprocess
from typing import Literal, Optional

from .base import BaseAnthropicTool, PowerShellResult, ToolError, ToolResult

class PowerShellTool(BaseAnthropicTool):
    """
    A tool that allows Claude to run PowerShell commands on Windows.
    """
    
    name = "bash"
    api_type = "bash_20250124"
    
    _process = None
    _timeout = 60.0  # default timeout in seconds
    
    def to_params(self) -> dict:
        """Returns the tool parameters for the Anthropic API."""
        return {
            "type": self.api_type,
            "name": self.name,
        }
        
    async def __call__(
        self, 
        command: Optional[str] = None, 
        restart: bool = False,
        **kwargs
    ) -> ToolResult:
        """Run a PowerShell command and return the result."""
        if restart:
            return await self._restart()
            
        if command is None:
            raise ToolError("No command provided")
            
        return await self._run_command(command)
    
    async def _restart(self) -> ToolResult:
        """Restart the PowerShell tool."""
        return PowerShellResult(system="PowerShell tool has been restarted.")
    
    async def _run_command(self, command: str) -> ToolResult:
        """Run a PowerShell command and return the result."""
        try:
            # Run PowerShell with the specified command
            process = await asyncio.create_subprocess_exec(
                "powershell.exe", 
                "-Command", 
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=self._timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return PowerShellResult(
                    error=f"Command timed out after {self._timeout} seconds"
                )
            
            stdout_text = stdout.decode('utf-8', errors='replace')
            stderr_text = stderr.decode('utf-8', errors='replace')
            
            return PowerShellResult(
                output=stdout_text if stdout_text else None,
                error=stderr_text if stderr_text else None
            )
        except Exception as e:
            return PowerShellResult(error=f"Failed to run PowerShell command: {str(e)}")