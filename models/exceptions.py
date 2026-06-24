class EngineError(Exception):
    pass

class LexerError(EngineError):
    pass

class ParseError(EngineError):
    pass

class SemanticError(EngineError):
    pass

class PlannerError(EngineError):
    pass

class ExecutionError(EngineError):
    pass
