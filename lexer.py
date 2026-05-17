"""
lexer.py
========
Analizador léxico (Lexer / Tokenizador) para el lenguaje de reglas.

Convierte el texto fuente en una lista plana de tokens que el parser
consumirá posteriormente.

Alfabeto (Σ) reconocido:
    Palabras clave : rule  if  then  AND
    Operadores     : :  >  <  =
    Literales      : id  (identificadores)   value  (enteros)

Reglas de formación:
    - Los identificadores comienzan con una letra o '_' y contienen
      letras, dígitos y '_'. Son case-sensitive; las palabras clave
      'rule', 'if', 'then' son minúsculas y 'AND' es mayúscula.
    - Los enteros son secuencias de dígitos (base 10, ≥ 0).
    - Los espacios en blanco (espacio, tabulación, salto de línea) se
      ignoran entre tokens.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import List


# ---------------------------------------------------------------------------
# Tipos de token
# ---------------------------------------------------------------------------

class TokenType(Enum):
    # ── Palabras clave ──────────────────────────────────────────────────────
    RULE  = "rule"   # introduce una regla
    IF    = "if"     # inicio de condición
    THEN  = "then"   # separador condición-acción
    AND   = "AND"    # conjunción (MAYÚSCULA obligatoria)

    # ── Operadores y puntuación ─────────────────────────────────────────────
    COLON = ":"      # separador tras el nombre de la regla
    GT    = ">"      # mayor que
    LT    = "<"      # menor que
    EQ    = "="      # igual a

    # ── Literales ───────────────────────────────────────────────────────────
    ID    = "ID"     # identificador (variable o nombre de hecho)
    VALUE = "VALUE"  # entero literal

    # ── Fin de entrada ───────────────────────────────────────────────────────
    EOF   = "EOF"


# Tabla de palabras clave → tipo de token correspondiente
KEYWORDS: dict[str, TokenType] = {
    "rule": TokenType.RULE,
    "if":   TokenType.IF,
    "then": TokenType.THEN,
    "AND":  TokenType.AND,
}


# ---------------------------------------------------------------------------
# Clase Token
# ---------------------------------------------------------------------------

@dataclass
class Token:
    """
    Unidad mínima de información léxica.

    Atributos:
        type  – categoría del token (TokenType)
        value – texto original en el fuente
        line  – número de línea (comienza en 1); útil para mensajes de error
    """
    type:  TokenType
    value: str
    line:  int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, line={self.line})"


# ---------------------------------------------------------------------------
# Excepción léxica
# ---------------------------------------------------------------------------

class LexerError(Exception):
    """Se lanza al encontrar un carácter no reconocido en el fuente."""


# ---------------------------------------------------------------------------
# Clase Lexer
# ---------------------------------------------------------------------------

class Lexer:
    """
    Analizador léxico para el lenguaje de reglas.

    Uso:
        tokens = Lexer(source_text).tokenize()

    El método tokenize() devuelve una lista de Token que termina
    siempre con un token EOF.
    """

    def __init__(self, source: str) -> None:
        self.source: str = source
        self.pos:    int = 0        # posición actual en el texto
        self.line:   int = 1        # número de línea actual

    # ── Utilidades de navegación ────────────────────────────────────────────

    def _current_char(self) -> str | None:
        """Devuelve el carácter actual sin consumirlo; None si fin de entrada."""
        if self.pos < len(self.source):
            return self.source[self.pos]
        return None

    def _advance(self) -> str:
        """Consume y devuelve el carácter actual; actualiza el contador de líneas."""
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
        return ch

    def _skip_whitespace(self) -> None:
        """Salta espacios, tabulaciones y saltos de línea."""
        while self._current_char() in (" ", "\t", "\r", "\n"):
            self._advance()

    # ── Lectores de lexemas ─────────────────────────────────────────────────

    def _read_identifier_or_keyword(self) -> Token:
        """
        Lee una secuencia de caracteres alfanuméricos y '_'.
        Clasifica el lexema como palabra clave o identificador.
        El cursor debe estar sobre el primer carácter (letra o '_').
        """
        start_line = self.line
        start      = self.pos

        while self._current_char() is not None and (
            self._current_char().isalnum() or self._current_char() == "_"
        ):
            self._advance()

        word       = self.source[start : self.pos]
        token_type = KEYWORDS.get(word, TokenType.ID)  # keyword o ID
        return Token(token_type, word, start_line)

    def _read_integer(self) -> Token:
        """
        Lee una secuencia de dígitos y la devuelve como token VALUE.
        El cursor debe estar sobre el primer dígito.
        """
        start_line = self.line
        start      = self.pos

        while self._current_char() is not None and self._current_char().isdigit():
            self._advance()

        return Token(TokenType.VALUE, self.source[start : self.pos], start_line)

    # ── Método principal ────────────────────────────────────────────────────

    def tokenize(self) -> List[Token]:
        """
        Recorre todo el texto fuente y produce la lista completa de tokens.
        El último elemento siempre es Token(EOF, '', <última_línea>).

        Lanza LexerError si encuentra un carácter no reconocido.
        """
        tokens: List[Token] = []

        while True:
            self._skip_whitespace()

            ch = self._current_char()

            # ── Fin de entrada ──────────────────────────────────────────────
            if ch is None:
                tokens.append(Token(TokenType.EOF, "", self.line))
                break

            current_line = self.line

            # ── Identificador o palabra clave ───────────────────────────────
            # Las palabras clave también empiezan con letra (rule, if, then, AND).
            if ch.isalpha() or ch == "_":
                tokens.append(self._read_identifier_or_keyword())

            # ── Entero literal ──────────────────────────────────────────────
            elif ch.isdigit():
                tokens.append(self._read_integer())

            # ── Operadores de un solo carácter ──────────────────────────────
            elif ch == ":":
                self._advance()
                tokens.append(Token(TokenType.COLON, ":", current_line))

            elif ch == ">":
                self._advance()
                tokens.append(Token(TokenType.GT, ">", current_line))

            elif ch == "<":
                self._advance()
                tokens.append(Token(TokenType.LT, "<", current_line))

            elif ch == "=":
                self._advance()
                tokens.append(Token(TokenType.EQ, "=", current_line))

            # ── Carácter no reconocido ──────────────────────────────────────
            else:
                raise LexerError(
                    f"Carácter no reconocido '{ch}' en la línea {self.line}"
                )

        return tokens
