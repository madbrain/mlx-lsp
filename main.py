import logging
from pygls.cli import start_server
from pygls.lsp.server import LanguageServer
from pygls.workspace import TextDocument
from lsprotocol import types
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class Span:
    start: int
    end: int

@dataclass
class Value:
    span: Span
    value: any

class LineParser:
    def __init__(self, content: str, add_error):
        self.content = content
        self.index = 0
        self.add_error = add_error

    def get_address(self):
        return self.get_value()
            
    def get_value(self):
        self.skip_whites()
        start = self.index
        while True:
            c = self.get_char()
            if c is None or self.is_delim(c):
                self.push_back(c)
                return self.convert_value(start)
            
    def get_values(self):
        values = []
        while not self.at_end():
            value = self.get_value()
            if value:
                values.append(value)
        return values
    
    def skip_whites(self):
        while True:
            c = self.get_char()
            if c is None or not self.is_space(c):
                self.push_back(c)
                return
            
    def expect(self, expected_c):
        self.skip_whites()
        c = self.get_char()
        if c != expected_c:
            self.add_error(Span(self.index-1, self.index), "expecting '%s'" % expected_c)
            return False
        return True
    
    def is_hex(self, c):
        return c >= 'a' and c <= 'z' or c >= 'A' and c <= 'Z' or c >= '0' and c <= '9'

    def is_space(self, c):
        return c == ' ' or c == '\t' or c == '\n'
    
    def is_delim(self, c):
        return c == ':' or self.is_space(c)
    
    def at_end(self):
        return self.index >= len(self.content)

    def get_char(self):
        if self.at_end():
            return None
        c = self.content[self.index]
        self.index += 1
        return c
    
    def push_back(self, c):
        if c:
            self.index -= 1

    def convert_value(self, start):
        span = Span(start, self.index)
        content = self.content[start:self.index]
        if len(content) == 0:
            return None
        try:
            return Value(span, int(content, 16))
        except ValueError:
            self.add_error(span, "bad value '%s'" % content)
            return None

class MLXLanguageServer(LanguageServer):

    def __init__(self):
        super().__init__("mlx-lang-server", "v0.1")

    def validate(self, doc: TextDocument):
        diagnostics = []
        current_addr = None
        
        for line, content in enumerate(doc.lines):
            def add_error(span: Span, message: str):
                diagnostics.append(
                    types.Diagnostic(
                        severity=types.DiagnosticSeverity.Error,
                        range=types.Range(
                            start=types.Position(line=line, character=span.start),
                            end=types.Position(line=line, character=span.end)),
                        message=message
                    )
                )
            parser = LineParser(content, add_error)
            addr = parser.get_address()
            if not addr:
                continue
            if not parser.expect(':'):
                continue
            values = parser.get_values()
            compute_checksum = len(values) > 0
            for value in values:
                if value.value < 0 or value.value > 255:
                    add_error(value.span, "bad value")
                    compute_checksum = False
            
            if compute_checksum:
                checksum = values[-1].value
                data = map(lambda v: v.value, values[0:-1])
                ck = int(addr.value / 256)
                ck = addr.value - 254*ck - (255 if ck > 127 else 0)
                ck = ck - (255 if ck > 255 else 0)
                for v in data:
                    ck = ck*2 - (255 if ck > 127 else 0) + v
                    ck = ck - (255 if ck > 255 else 0)
                if ck != checksum:
                    add_error(values[-1].span, "bad checksum (%s)" % hex(ck))

            if addr:
                if addr.value < 0 or addr.value > 0xFFFF:
                    add_error(addr.span, "bad addr")
                if current_addr and (current_addr + 8) != addr.value:
                    add_error(addr.span, "bad addr increment")
                current_addr = addr.value
        return diagnostics

server = MLXLanguageServer()

@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: MLXLanguageServer, params: types.DidOpenTextDocumentParams):
    """Parse each document when it is opened"""
    doc = ls.workspace.get_text_document(params.text_document.uri)
    diagnostics = ls.validate(doc)
    ls.text_document_publish_diagnostics(
        types.PublishDiagnosticsParams(
            uri=doc.uri,
            version=doc.version,
            diagnostics=diagnostics,
        )
    )

@server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: MLXLanguageServer, params: types.DidOpenTextDocumentParams):
    """Parse each document when it is changed"""
    doc = ls.workspace.get_text_document(params.text_document.uri)
    diagnostics = ls.validate(doc)
    ls.text_document_publish_diagnostics(
        types.PublishDiagnosticsParams(
            uri=doc.uri,
            version=doc.version,
            diagnostics=diagnostics,
        )
    )

#logging.basicConfig(filename='mlx-debug.log', filemode='w', level=logging.DEBUG)

if __name__ == "__main__":
    start_server(server)
