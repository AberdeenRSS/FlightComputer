from typing import Iterable
from app.logic.commands.command import Command
from app.logic.rocket_definition import Part, Rocket


def topological_sort(commands: Iterable[Part]) -> list[Part]:
    '''
    This algorithm assumes that the commands form a directed acyclic graph,
    where the commands are nodes and the dependencies are edges. The topological_sort function performs
    a depth-first search on the graph, adding each node to the result list only after all of its
    dependencies have already been added. The resulting list is then reversed to get the order of execution of the commands.
    (by chatGPT)
    '''
    visited = set()
    result = list()
    def dfs(node: Part):
        visited.add(node)
        for dependency in node.dependencies:
            if dependency not in visited:
                dfs(dependency)
        result.append(node)
    for command in commands:
        if command not in visited:
            dfs(command)
    return result[::-1]

