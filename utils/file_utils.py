from pathlib import Path
from typing import Union

def get_safe_filename(url: str) -> str:
    """
    將 URL 轉換為安全的文件名。
    
    Args:
        url (str): 要轉換的 URL。
    
    Returns:
        str: 安全的文件名。
    """
    url = url.split('://')[-1]
    safe_string = ''.join(c if c.isalnum() or c in '-._~' else '_' for c in url)
    return f"{safe_string[:200]}.txt"

def ensure_dir(directory: Union[str, Path]) -> Path:
    """
    確保指定的目錄存在，如果不存在則創建它。
    
    Args:
        directory (Union[str, Path]): 要確保存在的目錄路徑。
    
    Returns:
        Path: 目錄的 Path 對象。
    """
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path

def get_file_path(base_dir: Union[str, Path], source: str, feed: str, filename: str) -> Path:
    """
    根據給定的基礎目錄、來源、訂閱源和文件名生成完整的文件路徑。
    
    Args:
        base_dir (Union[str, Path]): 基礎目錄。
        source (str): 新聞來源。
        feed (str): 訂閱源。
        filename (str): 文件名。
    
    Returns:
        Path: 完整的文件路徑。
    """
    return ensure_dir(Path(base_dir) / f"{source}_{feed}") / filename
