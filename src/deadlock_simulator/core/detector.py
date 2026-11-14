"""Détection des cycles par parcours en profondeur."""


def find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    cycles: list[list[str]] = []
    done: set[str] = set()
    stack: list[str] = []
    in_stack: set[str] = set()

    def visit(node: str) -> None:
        if node in in_stack:
            start = stack.index(node)
            cycle = stack[start:] + [node]
            if cycle not in cycles:
                cycles.append(cycle)
            return
        if node in done:
            return
        in_stack.add(node)
        stack.append(node)
        for neighbor in graph.get(node, set()):
            visit(neighbor)
        stack.pop()
        in_stack.remove(node)
        done.add(node)

    for node in graph:
        visit(node)
    return cycles
