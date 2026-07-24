from abc import ABC, abstractmethod
from typing import IO, Any, Dict, List
from models.merger import QnAPair, InputFormat

class QnAParser(ABC):
    @abstractmethod
    def parse(self, file: IO[Any]) -> List[QnAPair]:
        """
        Parses an input file and extracts a list of QnAPair objects.
        
        Args:
            file: The input file-like object to parse.
            
        Returns:
            List[QnAPair]: The extracted question and answer pairs.
        """
        pass

class QnAParserFactory:
    _parsers: Dict[InputFormat, QnAParser] = {}

    @classmethod
    def register_parser(cls, format: InputFormat, parser: QnAParser) -> None:
        """
        Registers a QnAParser for a specific InputFormat.
        
        Args:
            format: The input format enum value.
            parser: The parser instance to register.
        """
        cls._parsers[format] = parser

    @classmethod
    def get_parser(cls, format: InputFormat) -> QnAParser:
        """
        Retrieves the registered parser for a specific format.
        
        Args:
            format: The input format to retrieve a parser for.
            
        Returns:
            QnAParser: The registered parser instance.
            
        Raises:
            ValueError: If no parser is registered for the format.
        """
        parser = cls._parsers.get(format)
        if not parser:
            raise ValueError(f"No parser registered for format: {format}")
        return parser

# Register default parsers
from services.json_qna_parser import JSONQnAParser
from services.txt_qna_parser import TXTQnAParser

QnAParserFactory.register_parser(InputFormat.json, JSONQnAParser())
QnAParserFactory.register_parser(InputFormat.txt, TXTQnAParser())
