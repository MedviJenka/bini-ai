import os
from typing import List
from crewai.tools import BaseTool
from pydantic import FilePath, Field


class FileReaderTool(BaseTool):
    """A tool for reading the content of a file."""

    name: str = "File Reader Tool"
    description: str = "Reads the content of a file given its filename. The filename should be relative to the tool's base_path."
    base_path: FilePath = Field(..., description="The base directory path from which files will be read.")

    def _run(self, filename: str) -> str:

        filepath = os.path.join(self.base_path, filename)
        try:
            with open(filepath, 'r') as f:
                return f.read()
        except FileNotFoundError:
            return f"Error: File not found at {filepath}"
        except Exception as e:
            return f"Error reading file {filepath}: {e}"


class FileWriterTool(BaseTool):
    """A tool for writing content to a file."""

    name: str = "File Writer Tool"
    description: str = "Writes content to a file. Requires a filename (relative to base_path) and the content to write."
    base_path: FilePath = Field(..., description="The base directory path where files will be written.")

    def _run(self, filename: str, content: str) -> str:
        filepath = os.path.join(self.base_path, filename)
        try:
            with open(filepath, 'w') as f:
                f.write(content)
            return f"Successfully wrote to {filepath}"
        except Exception as e:
            return f"Error writing to file {filepath}: {e}"


class FileListTool(BaseTool):
    """A tool for listing files and directories within a specified directory."""

    name: str = "File List Tool"
    description: str = "Lists files and directories in a specified path. The path should be relative to the tool's base_path. Defaults to listing the base_path itself."
    base_path: FilePath = Field(..., description="The base directory path from which to list files.")

    def _run(self, directory: str = ".") -> List[str]:
        filepath = os.path.join(self.base_path, directory)
        try:
            return os.listdir(filepath)
        except FileNotFoundError:
            return [f"Error: Directory not found at {filepath}"]
        except Exception as e:
            return [f"Error listing files in {filepath}: {e}"]
