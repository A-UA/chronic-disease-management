"""DOCX 文档解析器插件"""
from io import BytesIO
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from app.plugins.parser.base import DocumentParseError, ParseResult, normalize_text
from app.plugins.registry import PluginRegistry


class DocxParserPlugin:
    supported_types = [".docx"]

    def parse(self, file_bytes: bytes, filename: str) -> ParseResult:
        try:
            with ZipFile(BytesIO(file_bytes)) as archive:
                document_xml = archive.read("word/document.xml")
        except KeyError as exc:
            raise DocumentParseError("DOCX document is missing word/document.xml") from exc
        except BadZipFile as exc:
            raise DocumentParseError("DOCX document is invalid or corrupted") from exc

        root = ElementTree.fromstring(document_xml)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

        def _extract_text_recursive(element) -> list[str]:
            texts: list[str] = []
            for child in element:
                if child.tag.endswith("}p"):
                    t_nodes = child.findall(".//w:t", namespace)
                    p_text = "".join(node.text or "" for node in t_nodes).strip()
                    if p_text:
                        texts.append(p_text)
                elif child.tag.endswith("}tbl"):
                    table_texts: list[str] = []
                    for row in child.findall(".//w:tr", namespace):
                        row_cells = []
                        for cell in row.findall(".//w:tc", namespace):
                            cell_text = " ".join(_extract_text_recursive(cell)).strip()
                            row_cells.append(cell_text)
                        if any(row_cells):
                            table_texts.append(" | ".join(row_cells))
                    if table_texts:
                        texts.append("\n" + "\n".join(table_texts) + "\n")
                elif child.tag.endswith("}body") or child.tag.endswith("}sdtContent"):
                    texts.extend(_extract_text_recursive(child))
            return texts

        body = root.find("w:body", namespace)
        if body is None:
            return ParseResult(text="", pages=[])

        all_texts = _extract_text_recursive(body)
        text = normalize_text("\n\n".join(all_texts))
        return ParseResult(text=text, pages=[text] if text else [])


PluginRegistry.register("parser", "docx", lambda: DocxParserPlugin())
