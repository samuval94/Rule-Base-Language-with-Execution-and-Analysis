"""
parser.py
=========
Analizador sintáctico LL(1) por descenso recursivo para el lenguaje de reglas.

Gramática original (NO LL(1) por recursión izquierda en Cond):
    Program  → RuleList
    RuleList → Rule RuleList | ε
    Rule     → rule id : if Cond then Action
    Cond     → Cond AND Cond | Atom
    Atom     → id RelOp value | id
    RelOp    → > | < | =
    Action   → id

Transformación a LL(1) (eliminación de recursión izquierda en Cond):
    Program   → RuleList EOF
    RuleList  → Rule RuleList | ε
    Rule      → RULE ID COLON IF Cond THEN Action
    Cond      → Atom CondRest
    CondRest  → AND Atom CondRest | ε
    Atom      → ID AtomRest
    AtomRest  → RelOp VALUE | ε
    RelOp     → GT | LT | EQ
    Action    → ID

Verificación LL(1):
    - RuleList : FIRST(Rule)={RULE}  vs  FOLLOW(RuleList)={EOF}      → OK
    - CondRest : FIRST(AND...)={AND} vs  FOLLOW(CondRest)={THEN}     → OK
    - AtomRest : FIRST(RelOp)={>,<,=} vs FOLLOW(AtomRest)={AND,THEN} → OK

La AND es left-associative por la forma de CondRest; semánticamente es
equivalente ya que AND es conmutativo y asociativo.
"""

from __future__ import annotations

from typing import List

from lexer import Lexer, LexerError, Token, TokenType
from ast_nodes import (
    Action,
    AndCondition,
    CompCondition,
    Condition,
    FactCondition,
    Program,
    Rule,
)


# ---------------------------------------------------------------------------
# Excepción sintáctica
# ---------------------------------------------------------------------------

class ParseError(Exception):
    """Se lanza cuando los tokens no se ajustan a la gramática."""


# ---------------------------------------------------------------------------
# Parser LL(1) por descenso recursivo
# ---------------------------------------------------------------------------

class Parser:
    """
    Construye un AST a partir de una lista de tokens producida por el Lexer.

    Cada método parse_<X>() implementa la producción gramatical <X>.
    """

    def __init__(self, tokens: List[Token]) -> None:
        self.tokens: List[Token] = tokens
        self.pos:    int         = 0       # índice del token actual

    # ── Navegación por los tokens ───────────────────────────────────────────

    def _current(self) -> Token:
        """Token actual sin consumirlo."""
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        """Consume y devuelve el token actual."""
        token = self.tokens[self.pos]
        # No avanzar más allá del último token (EOF)
        if self.pos < len(self.tokens) - 1:
            self.pos += 1
        return token

    def _expect(self, ttype: TokenType) -> Token:
        """
        Consume el token actual verificando que sea del tipo esperado.
        Lanza ParseError si no coincide.
        """
        token = self._current()
        if token.type != ttype:
            raise ParseError(
                f"Línea {token.line}: se esperaba '{ttype.name}', "
                f"pero se encontró '{token.type.name}' ({token.value!r})"
            )
        return self._advance()

    # ── Producciones gramaticales ───────────────────────────────────────────

    def parse_program(self) -> Program:
        """
        Program → RuleList EOF

        Punto de entrada del parser. Produce el nodo raíz Program.
        """
        rules = self._parse_rule_list()
        self._expect(TokenType.EOF)           # verifica que no haya texto sobrante
        return Program(rules=rules)

    def _parse_rule_list(self) -> List[Rule]:
        """
        RuleList → Rule RuleList | ε

        FIRST(Rule) = {RULE}
        FOLLOW(RuleList) = {EOF}

        Se sigue produciendo mientras el token actual sea RULE.
        """
        rules: List[Rule] = []
        while self._current().type == TokenType.RULE:
            rules.append(self._parse_rule())
        return rules

    def _parse_rule(self) -> Rule:
        """
        Rule → RULE ID COLON IF Cond THEN Action

        Ejemplo de entrada:
            rule r1: if temp > 30 then alert
        """
        self._expect(TokenType.RULE)               # 'rule'
        name_token = self._expect(TokenType.ID)    # nombre de la regla (ej. 'r1')
        self._expect(TokenType.COLON)              # ':'
        self._expect(TokenType.IF)                 # 'if'
        condition = self._parse_cond()             # condición (puede ser compuesta)
        self._expect(TokenType.THEN)               # 'then'
        action = self._parse_action()              # acción (identificador de hecho)

        return Rule(
            name      = name_token.value,
            condition = condition,
            action    = action,
        )

    def _parse_cond(self) -> Condition:
        """
        Cond → Atom CondRest

        Parsea la condición completa (puede contener múltiples AND).
        El átomo izquierdo se pasa a CondRest para construir el árbol AND.
        """
        left = self._parse_atom()          # primer átomo
        return self._parse_cond_rest(left) # posibles extensiones con AND

    def _parse_cond_rest(self, left: Condition) -> Condition:
        """
        CondRest → AND Atom CondRest | ε

        FIRST(AND Atom CondRest) = {AND}
        FOLLOW(CondRest)         = {THEN}

        Construye nodos AndCondition de izquierda a derecha.
        Ejemplo: a AND b AND c → And(And(a, b), c)
        """
        if self._current().type == TokenType.AND:
            self._advance()                        # consume 'AND'
            right_atom = self._parse_atom()        # siguiente átomo
            combined   = AndCondition(left=left, right=right_atom)
            return self._parse_cond_rest(combined) # continúa con más AND (si los hay)

        # Producción ε: el token siguiente debe estar en FOLLOW(CondRest) = {THEN}
        return left

    def _parse_atom(self) -> Condition:
        """
        Atom     → ID AtomRest
        AtomRest → RelOp VALUE | ε

        FIRST(AtomRest) = {GT, LT, EQ}
        FOLLOW(AtomRest) = {AND, THEN}

        Si al identificador le sigue un operador relacional, es una comparación.
        Si no, es una condición de hecho (FactCondition).
        """
        id_token = self._expect(TokenType.ID)      # identificador

        # Lookahead: ¿sigue un operador relacional?
        if self._current().type in (TokenType.GT, TokenType.LT, TokenType.EQ):
            op        = self._parse_relop()               # operador
            val_token = self._expect(TokenType.VALUE)     # valor entero
            return CompCondition(
                identifier = id_token.value,
                operator   = op,
                value      = int(val_token.value),
            )

        # Sin operador → condición de hecho
        return FactCondition(identifier=id_token.value)

    def _parse_relop(self) -> str:
        """
        RelOp → GT | LT | EQ

        Devuelve el operador como cadena: '>', '<' o '='.
        """
        token = self._current()
        if token.type == TokenType.GT:
            self._advance()
            return ">"
        elif token.type == TokenType.LT:
            self._advance()
            return "<"
        elif token.type == TokenType.EQ:
            self._advance()
            return "="
        raise ParseError(
            f"Línea {token.line}: se esperaba operador relacional "
            f"(>, <, =), pero se encontró '{token.type.name}'"
        )

    def _parse_action(self) -> Action:
        """
        Action → ID

        La acción siempre es un único identificador (el hecho a activar).
        """
        id_token = self._expect(TokenType.ID)
        return Action(identifier=id_token.value)


# ---------------------------------------------------------------------------
# Función de conveniencia
# ---------------------------------------------------------------------------

def parse(source: str) -> Program:
    """
    Pipeline completo: texto fuente → lista de tokens → AST.

    Args:
        source: texto del programa (sección de reglas, sin el estado).

    Returns:
        Program con la lista de reglas parseadas.

    Raises:
        LexerError: si hay un carácter no reconocido.
        ParseError: si la estructura no sigue la gramática.
    """
    tokens  = Lexer(source).tokenize()
    program = Parser(tokens).parse_program()
    return program
