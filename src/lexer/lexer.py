from models.tokens import Token, TokenType
from models.exceptions import LexerError

_KEYWORDS: dict[str, TokenType] = {
    "SELECT": TokenType.SELECT,
    "FROM":   TokenType.FROM,
    "WHERE":  TokenType.WHERE,
    "ORDER":  TokenType.ORDER,
    "BY":     TokenType.BY,
    "GROUP":  TokenType.GROUP,
}


class Lexer:
    def __init__(self, input: str) -> None:
        self._input = input
        self._pos = 0

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []

        while self._pos < len(self._input):
            ch = self._input[self._pos]

            if ch in " \t\n\r":
                self._pos += 1

            elif ch.isalpha() or ch == "_":
                word = self._read_identifier()
                ttype = _KEYWORDS.get(word.upper(), TokenType.IDENTIFIER)
                tokens.append(Token(type=ttype, value=word))

            elif ch.isdigit():
                num, ttype = self._read_number()
                tokens.append(Token(type=ttype, value=num))

            elif ch == "*":
                tokens.append(Token(type=TokenType.STAR, value="*"))
                self._pos += 1

            elif ch == ">" and self._peek_next() == "=":
                tokens.append(Token(type=TokenType.GTE, value=">="))
                self._pos += 2
            elif ch == ">":
                tokens.append(Token(type=TokenType.GT, value=">"))
                self._pos += 1

            elif ch == "<" and self._peek_next() == "=":
                tokens.append(Token(type=TokenType.LTE, value="<="))
                self._pos += 2
            elif ch == "<":
                tokens.append(Token(type=TokenType.LT, value="<"))
                self._pos += 1

            elif ch == "=":
                tokens.append(Token(type=TokenType.EQ, value="="))
                self._pos += 1

            elif ch == "!" and self._peek_next() == "=":
                tokens.append(Token(type=TokenType.NEQ, value="!="))
                self._pos += 2

            elif ch == ",":
                tokens.append(Token(type=TokenType.COMMA, value=","))
                self._pos += 1

            elif ch == ";":
                tokens.append(Token(type=TokenType.SEMICOLON, value=";"))
                self._pos += 1

            elif ch == "(":
                tokens.append(Token(type=TokenType.LPAREN, value="("))
                self._pos += 1

            elif ch == ")":
                tokens.append(Token(type=TokenType.RPAREN, value=")"))
                self._pos += 1

            elif ch == "'":
                s = self._read_string()
                tokens.append(Token(type=TokenType.STRING, value=s))

            else:
                raise LexerError(f"Unexpected character: '{ch}' at position {self._pos}")

        tokens.append(Token(type=TokenType.EOF, value=""))
        return tokens

    def _peek_next(self) -> str:
        nxt = self._pos + 1
        return self._input[nxt] if nxt < len(self._input) else ""

    def _read_identifier(self) -> str:
        start = self._pos
        while self._pos < len(self._input) and (
            self._input[self._pos].isalnum() or self._input[self._pos] == "_"
        ):
            self._pos += 1
        return self._input[start : self._pos]

    def _read_number(self) -> tuple[str, TokenType]:
        start = self._pos
        ttype = TokenType.INTEGER
        while self._pos < len(self._input) and (
            self._input[self._pos].isdigit() or self._input[self._pos] == "."
        ):
            if self._input[self._pos] == ".":
                ttype = TokenType.FLOAT
            self._pos += 1
        return self._input[start : self._pos], ttype

    def _read_string(self) -> str:
        self._pos += 1  # skip opening quote
        start = self._pos
        while self._pos < len(self._input) and self._input[self._pos] != "'":
            self._pos += 1
        if self._pos >= len(self._input):
            raise LexerError("Unterminated string literal")
        s = self._input[start : self._pos]
        self._pos += 1  # skip closing quote
        return s
