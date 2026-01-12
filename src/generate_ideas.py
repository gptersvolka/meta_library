"""
아이디어 생성 모듈 (alias)
실제 구현: 06_generate_ideas.py
"""
import importlib

_module = importlib.import_module("src.06_generate_ideas")

analyze_patterns = _module.analyze_patterns
generate_ideas_from_patterns = _module.generate_ideas_from_patterns
generate_all_ideas = _module.generate_all_ideas

__all__ = ["analyze_patterns", "generate_ideas_from_patterns", "generate_all_ideas"]
