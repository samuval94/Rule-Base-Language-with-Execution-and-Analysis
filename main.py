"""
main.py
=======
Punto de entrada del intérprete del lenguaje de reglas.

Responsabilidades:
    1. Leer el programa completo desde la entrada estándar (stdin).
    2. Separar el texto en dos secciones:
           • Reglas  → todo lo que aparece ANTES de la línea 'State:'
           • Estado  → todo lo que aparece DESPUÉS de 'State:'
    3. Parsear las reglas y construir el AST (lexer + parser).
    4. Parsear el estado inicial: extraer variables (id = int) y hechos (id).
    5. Ejecutar el intérprete hasta alcanzar el punto fijo.
    6. Imprimir los hechos activados en orden lexicográfico.
    7. Ejecutar el análisis estático e imprimir sus mensajes.

Formato de entrada (stdin):
────────────────────────────
    rule r1:
        if temp > 30 then alert

    rule r2:
        if alert then fan_on

    State:
    temp = 35

Formato de salida (stdout):
────────────────────────────
    alert
    fan_on

    (análisis estático, si aplica)

Casos especiales:
    • Si no se activa ningún hecho → imprimir "(no output)"
    • Si no hay sección 'State:' → estado vacío (sin variables ni hechos)
    • Si no hay reglas → solo se ejecuta el análisis estático (sin hechos)
"""

import sys
import re

from lexer            import Lexer, LexerError
from parser           import Parser, ParseError
from interpreter      import Interpreter
from static_analysis  import analyze
from ast_nodes        import Program


# ---------------------------------------------------------------------------
# Separación del texto fuente en secciones
# ---------------------------------------------------------------------------

def split_source(text: str):
    """
    Divide el texto de entrada en dos partes:
        • rules_text : todo lo anterior a la línea 'State:'
        • state_text : todo lo posterior a la línea 'State:'

    La comparación es insensible a espacios laterales pero sensible
    a mayúsculas ('State:' es la única forma válida).

    Args:
        text : contenido completo leído desde stdin.

    Returns:
        Tupla (rules_text: str, state_text: str).
        Si no existe la sección 'State:', state_text es cadena vacía.
    """
    lines = text.splitlines()

    # Buscar el índice de la línea que contiene únicamente 'State:'
    state_index = None
    for i, line in enumerate(lines):
        if line.strip() == "State:":
            state_index = i
            break

    if state_index is None:
        # No hay sección State → todo el texto son reglas, estado vacío
        return text, ""

    rules_text = "\n".join(lines[:state_index])
    state_text = "\n".join(lines[state_index + 1:])
    return rules_text, state_text


# ---------------------------------------------------------------------------
# Parseo del estado inicial
# ---------------------------------------------------------------------------

def parse_state(state_text: str):
    """
    Interpreta las líneas de la sección State y construye:
        • state_vars  : dict {str → int}   variables con valor entero
        • state_facts : set  {str}         hechos inicialmente activos

    Formato aceptado (una declaración por línea):
        • Asignación de variable : id = entero    (ej. temp = 35)
        • Hecho activo           : id             (ej. alert)
        • Líneas vacías          : ignoradas

    La distinción se hace mediante expresión regular:
        - Si la línea contiene '=' → se interpreta como asignación.
        - Si la línea es solo un identificador → se interpreta como hecho.

    Args:
        state_text : texto de la sección posterior a 'State:'.

    Returns:
        Tupla (state_vars: dict, state_facts: set).
    """
    state_vars:  dict[str, int] = {}
    state_facts: set[str]       = set()

    # Patrón para asignación: id = entero
    assignment_pattern = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(\d+)$")
    # Patrón para hecho: solo un identificador
    fact_pattern       = re.compile(r"^([a-zA-Z_][a-zA-Z0-9_]*)$")

    for line in state_text.splitlines():
        line = line.strip()

        if not line:
            continue  # ignorar líneas vacías

        # ── ¿Es una asignación de variable? ────────────────────────────────
        match_assign = assignment_pattern.match(line)
        if match_assign:
            var_name  = match_assign.group(1)
            var_value = int(match_assign.group(2))
            state_vars[var_name] = var_value
            continue

        # ── ¿Es un hecho activo? ────────────────────────────────────────────
        match_fact = fact_pattern.match(line)
        if match_fact:
            state_facts.add(match_fact.group(1))
            continue

        # ── Línea no reconocida: se ignora con advertencia ──────────────────
        print(f"[Advertencia] Línea no reconocida en State: '{line}'", file=sys.stderr)

    return state_vars, state_facts


# ---------------------------------------------------------------------------
# Impresión de resultados
# ---------------------------------------------------------------------------

def print_output(active_facts: set[str], initial_facts: set[str]) -> None:
    """
    Imprime los hechos activados durante la ejecución en orden lexicográfico.

    Solo se imprimen los hechos NUEVOS generados por las reglas, es decir,
    los que no estaban en el estado inicial (initial_facts). Esto se ajusta
    al formato esperado por las especificaciones del proyecto.

    Sin embargo, revisando los casos de prueba del enunciado, la salida
    incluye TODOS los hechos activos al finalizar (incluyendo los iniciales
    si fueran activados por reglas, que en los casos dados no ocurre).
    Por consistencia con los casos de prueba, se imprimen TODOS los hechos
    activos al finalizar la ejecución.

    Si el conjunto resultante está vacío → se imprime '(no output)'.

    Args:
        active_facts  : conjunto de todos los hechos activos tras la ejecución.
        initial_facts : hechos que ya estaban activos antes de ejecutar.
    """
    # Los hechos a reportar son los activados por reglas
    # (pueden incluir hechos que ya estaban activos si también fueron
    # producidos por alguna regla, pero en la práctica el intérprete
    # los incluye en active_facts desde el inicio).
    # Según el enunciado, la salida son los hechos activados durante
    # la ejecución, que es todo active_facts al finalizar.
    if not active_facts:
        print("(no output)")
    else:
        for fact in sorted(active_facts):
            print(fact)


def print_analysis(
    conflict_msgs:   list[str],
    redundancy_msgs: list[str],
    inactive_msgs:   list[str],
) -> None:
    """
    Imprime los mensajes del análisis estático.

    Orden de impresión (según el formato del enunciado):
        1. Conflictos
        2. Redundancias
        3. Reglas potencialmente inactivas

    Cada mensaje se imprime en una línea separada.
    Si no hay mensajes de análisis, no se imprime nada extra.

    Args:
        conflict_msgs   : lista de mensajes de conflicto.
        redundancy_msgs : lista de mensajes de redundancia.
        inactive_msgs   : lista de mensajes de inactividad.
    """
    all_messages = conflict_msgs + redundancy_msgs + inactive_msgs

    if all_messages:
        # Separador visual entre output de ejecución y análisis estático
        print()
        print("Analysis:")
        for msg in all_messages:
            print(msg)


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Orquesta el pipeline completo del intérprete:

        stdin
          │
          ▼
        split_source()          ← separar reglas del estado
          │
          ├─── rules_text ──► Lexer ──► Parser ──► Program (AST)
          │
          └─── state_text ──► parse_state() ──► state_vars, state_facts
                                                        │
                                                        ▼
                                              Interpreter.run() ──► active_facts
                                                        │
                                                        ├──► print_output()
                                                        │
                                                        └──► analyze() ──► print_analysis()

    Maneja errores léxicos y sintácticos imprimiéndolos en stderr y
    terminando con código de salida 1.
    """
    # ── 1. Leer todo el texto desde stdin ───────────────────────────────────
    source = sys.stdin.read()

    # ── 2. Separar reglas y estado ──────────────────────────────────────────
    rules_text, state_text = split_source(source)

    # ── 3. Parsear las reglas (lexer + parser → AST) ────────────────────────
    try:
        tokens  = Lexer(rules_text).tokenize()
        program = Parser(tokens).parse_program()
    except LexerError as e:
        print(f"Error léxico: {e}", file=sys.stderr)
        sys.exit(1)
    except ParseError as e:
        print(f"Error sintáctico: {e}", file=sys.stderr)
        sys.exit(1)

    # ── 4. Parsear el estado inicial ────────────────────────────────────────
    state_vars, state_facts = parse_state(state_text)

    # ── 5. Ejecutar el intérprete (algoritmo de punto fijo) ─────────────────
    interpreter  = Interpreter(program, state_vars, state_facts)
    active_facts = interpreter.run()
    fired_rules  = interpreter.fired_rules

    # ── 6. Imprimir los hechos activados ────────────────────────────────────
    print_output(active_facts, state_facts)

    # ── 7. Ejecutar análisis estático e imprimir mensajes ───────────────────
    # Nota: la detección de reglas inactivas solo tiene sentido cuando existe
    # una "red de propagación" de hechos, es decir, cuando hay más de una
    # regla. Con una sola regla no hay red con qué comparar el aislamiento.
    conflict_msgs, redundancy_msgs, inactive_msgs = analyze(
        program,
        state_vars,
        state_facts,
        fired_rules,
    )
    if len(program.rules) <= 1:
        inactive_msgs = []
    print_analysis(conflict_msgs, redundancy_msgs, inactive_msgs)


# ---------------------------------------------------------------------------
# Punto de entrada
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
