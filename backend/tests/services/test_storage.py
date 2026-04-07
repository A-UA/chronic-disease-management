"""存储服务测试：文件名安全化"""
from app.core.storage import _sanitize_filename


class TestSanitizeFilename:
    def test_normal_filename(self):
        """正常文件名应保留扩展名"""
        result = _sanitize_filename("report.pdf")
        assert result.endswith(".pdf")
        assert "report" in result

    def test_path_traversal_blocked(self):
        """路径穿越字符应被去除"""
        result = _sanitize_filename("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result
        assert "passwd" in result

    def test_chinese_filename(self):
        """中文文件名应保留"""
        result = _sanitize_filename("患者报告.docx")
        assert "患者报告" in result
        assert result.endswith(".docx")

    def test_special_characters_removed(self):
        """特殊字符应被替换为下划线"""
        result = _sanitize_filename("file name (1)!@#.pdf")
        assert ".pdf" in result
        # 不应包含括号、感叹号等
        assert "(" not in result
        assert "!" not in result

    def test_uuid_prefix_ensures_uniqueness(self):
        """同一文件名应生成不同的安全名称"""
        r1 = _sanitize_filename("test.txt")
        r2 = _sanitize_filename("test.txt")
        assert r1 != r2  # UUID 前缀不同

    def test_empty_filename(self):
        """空文件名应生成有效的 UUID 名称"""
        result = _sanitize_filename("")
        assert len(result) > 0

    def test_windows_path(self):
        """Windows 路径应被正确处理"""
        result = _sanitize_filename("C:\\Users\\test\\report.pdf")
        assert ".." not in result
        assert "report" in result
