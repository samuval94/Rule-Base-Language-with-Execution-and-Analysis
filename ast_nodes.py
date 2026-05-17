"""
ast_nodes.py
============
Definición de los nodos del Árbol de Sintaxis Abstracta (AST).

Jerarquía:
    Program
    └── Rule (lista)
         ├── name        : str
         ├── condition   : Condition  (CompCondition | FactCondition | AndCondition)
         └── action      : Action

Tipos de condición:
    CompCondition  → id RelOp value    (comparación con variable entera)
    FactCondition  → id                (verdadero si el hecho está activo)
    AndCondition   → Condition AND Condition
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Union


# ---------------------------------------------------------------------------
# Nodos de condición
# ---------------------------------------------------------------------------

@dataclass
class CompCondition:
    """
    Condición de comparación: <identifier> <operator> <value>
    Ejemplo: temp > 30
    """
    identifier: str       # nombre de la variable
    operator:   str       # '>', '<' o '='
    value:      int       # valor entero con el que se compara


@dataclass
class FactCondition:
    """
    Condición de hecho: solo un identificador.
    Es verdadera si el identificador está activo como hecho en el estado actual.
    Ejemplo: alert
    """
    identifier: str


@dataclass
class AndCondition:
    """
    Conjunción lógica de dos condiciones.
    Es verdadera si y solo si ambas sub-condiciones son verdaderas.
    Ejemplo: temp > 30 AND humidity < 50
    """
    left:  "Condition"
    right: "Condition"


# Alias de tipo para cualquier condición válida
Condition = Union[CompCondition, FactCondition, AndCondition]


# ---------------------------------------------------------------------------
# Nodo de acción
# ---------------------------------------------------------------------------

@dataclass
class Action:
    """
    Acción que activa un hecho al dispararse una regla.
    Ejemplo: then alert  →  Action(identifier='alert')
    """
    identifier: str


# ---------------------------------------------------------------------------
# Nodo de regla
# ---------------------------------------------------------------------------

@dataclass
class Rule:
    """
    Regla completa: rule <name>: if <condition> then <action>
    Ejemplo:
        rule r1:
            if temp > 30 then alert
    →   Rule(name='r1',
             condition=CompCondition('temp', '>', 30),
             action=Action('alert'))
    """
    name:      str        # identificador de la regla (ej. 'r1')
    condition: Condition  # condición de disparo
    action:    Action     # acción a ejecutar si la condición es verdadera


# ---------------------------------------------------------------------------
# Nodo raíz del programa
# ---------------------------------------------------------------------------

@dataclass
class Program:
    """
    Nodo raíz del AST. Contiene la lista de todas las reglas del programa.
    """
    rules: List[Rule] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Utilidad: impresión legible del AST (solo para depuración)
# ---------------------------------------------------------------------------

def condition_str(cond: Condition, indent: int = 0) -> str:
    """Representación en texto de una condición (para depuración)."""
    pad = "  " * indent
    if isinstance(cond, CompCondition):
        return f"{pad}Cmp({cond.identifier} {cond.operator} {cond.value})"
    elif isinstance(cond, FactCondition):
        return f"{pad}Fact({cond.identifier})"
    elif isinstance(cond, AndCondition):
        left  = condition_str(cond.left,  indent + 1)
        right = condition_str(cond.right, indent + 1)
        return f"{pad}And(\n{left},\n{right}\n{pad})"
    return f"{pad}Unknown"


def print_ast(program: Program) -> None:
    """Imprime el AST completo de forma legible (para depuración)."""
    print("Program:")
    for rule in program.rules:
        print(f"  Rule '{rule.name}':")
        print(f"    Condition:\n{condition_str(rule.condition, 3)}")
        print(f"    Action: Activate('{rule.action.identifier}')")
