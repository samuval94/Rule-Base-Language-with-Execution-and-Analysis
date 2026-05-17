"""
interpreter.py
==============
Intérprete de punto fijo para el lenguaje de reglas.

Modelo de ejecución (Canonical Evaluation Strategy):
─────────────────────────────────────────────────────
El programa se evalúa sobre un ESTADO formado por:
    • state_vars  : dict {str → int}   variables con sus valores enteros (inmutables)
    • active_facts: set  {str}         hechos activos (crece monotónicamente)

Algoritmo de punto fijo:
    1. Inicializar active_facts con los hechos del estado inicial.
    2. Repetir:
       a. Evaluar la condición de cada regla contra el estado actual.
       b. Si la condición es verdadera → el hecho de la acción se "activa".
       c. Agregar los nuevos hechos a active_facts.
    3. Hasta que no se agreguen nuevos hechos (punto fijo alcanzado).

Determinismo: el resultado es independiente del orden de evaluación de las
reglas, ya que los hechos solo se agregan (nunca se eliminan) y la
evaluación de una regla no modifica state_vars.
"""

from __future__ import annotations

from typing import Dict, Set

from ast_nodes import (
    AndCondition,
    CompCondition,
    Condition,
    FactCondition,
    Program,
)


class Interpreter:
    """
    Evalúa un programa de reglas hasta alcanzar el punto fijo.

    Atributos públicos después de llamar a run():
        active_facts : set[str]  – todos los hechos activados (incluye los iniciales)
        fired_rules  : set[str]  – nombres de las reglas que dispararon al menos una vez
    """

    def __init__(
        self,
        program:     Program,
        state_vars:  Dict[str, int],
        state_facts: Set[str],
    ) -> None:
        """
        Args:
            program     : AST del programa.
            state_vars  : asignaciones de variables del estado inicial  (ej. {'temp': 35}).
            state_facts : hechos activos en el estado inicial           (ej. {'a'}).
        """
        self.program      = program
        self.state_vars   = state_vars              # variables enteras (no cambian)
        self.active_facts = set(state_facts)        # hechos activos (crecen)
        self.fired_rules: Set[str] = set()          # reglas que dispararon

    # ── Evaluación de condiciones ───────────────────────────────────────────

    def _eval_condition(self, cond: Condition) -> bool:
        """
        Evalúa recursivamente una condición contra el estado actual.

        CompCondition (id RelOp value):
            • Si la variable existe en state_vars, compara su valor con 'value'.
            • Si la variable NO está definida, devuelve False
              (variable desconocida no satisface ninguna comparación).

        FactCondition (id):
            • Verdadera si y solo si el identificador está en active_facts.

        AndCondition (cond1 AND cond2):
            • Verdadera si y solo si ambas sub-condiciones son verdaderas.
            • Usa evaluación en cortocircuito (short-circuit).
        """
        if isinstance(cond, CompCondition):
            # Obtener el valor de la variable (None si no está definida)
            val = self.state_vars.get(cond.identifier)
            if val is None:
                return False           # variable no definida → condición falsa

            op, v = cond.operator, cond.value
            if op == ">": return val > v
            if op == "<": return val < v
            if op == "=": return val == v
            return False               # operador desconocido (no debería ocurrir)

        elif isinstance(cond, FactCondition):
            return cond.identifier in self.active_facts

        elif isinstance(cond, AndCondition):
            # Cortocircuito: si left es falso, no evalúa right
            return (
                self._eval_condition(cond.left)
                and self._eval_condition(cond.right)
            )

        return False

    # ── Algoritmo principal ─────────────────────────────────────────────────

    def run(self) -> Set[str]:
        """
        Ejecuta el programa hasta alcanzar el punto fijo.

        En cada iteración:
            1. Evalúa todas las reglas.
            2. Recoge los hechos generados por reglas cuya condición sea verdadera.
            3. Si se generaron hechos nuevos (no presentes en active_facts),
               los agrega y repite.
            4. Si no hay hechos nuevos → punto fijo alcanzado → termina.

        Returns:
            El conjunto final de hechos activos (state_facts iniciales + activados).
        """
        while True:
            new_facts: Set[str] = set()  # hechos generados en esta iteración

            for rule in self.program.rules:
                if self._eval_condition(rule.condition):
                    # La regla disparó: marcarla y recoger su acción
                    self.fired_rules.add(rule.name)
                    fact = rule.action.identifier
                    if fact not in self.active_facts:
                        new_facts.add(fact)  # hecho genuinamente nuevo

            if not new_facts:
                break  # ── Punto fijo alcanzado: no hay hechos nuevos ──

            # Agregar los nuevos hechos al estado para la siguiente iteración
            self.active_facts |= new_facts

        return self.active_facts
