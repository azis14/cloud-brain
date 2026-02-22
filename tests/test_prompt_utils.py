"""
Unit tests for prompt_utils.py
"""
import pytest
from utils.prompt_utils import PromptUtils


class TestBuildIdentifyPrompt:
    """Tests for build_identify_prompt method."""
    
    def test_build_identify_prompt_basic(self):
        """Test building identify prompt with basic message."""
        message = "Hello, how are you?"
        prompt = PromptUtils.build_identify_prompt(message)
        
        assert "Hello, how are you?" in prompt
        assert "QUERY" in prompt
        assert "SYNC" in prompt
        assert "UNKNOWN" in prompt
        assert "You are an AI assistant" in prompt
    
    def test_build_identify_prompt_sync_command(self):
        """Test building identify prompt with sync command."""
        message = "Sync the database now"
        prompt = PromptUtils.build_identify_prompt(message)
        
        assert "Sync the database now" in prompt
        assert "QUERY" in prompt
        assert "SYNC" in prompt
        assert "UNKNOWN" in prompt
    
    def test_build_identify_prompt_empty_message(self):
        """Test building identify prompt with empty message."""
        message = ""
        prompt = PromptUtils.build_identify_prompt(message)
        
        assert "Message: " in prompt
        assert "QUERY" in prompt
        assert "SYNC" in prompt
        assert "UNKNOWN" in prompt
    
    def test_build_identify_prompt_special_characters(self):
        """Test building identify prompt with special characters."""
        message = "What is AI/ML? & how does it work?"
        prompt = PromptUtils.build_identify_prompt(message)
        
        assert "What is AI/ML? & how does it work?" in prompt


class TestBuildQuestionPrompt:
    """Tests for build_question_prompt method."""
    
    def test_build_question_prompt_basic(self):
        """Test building question prompt with basic question and context."""
        question = "What is AI?"
        context = "AI stands for Artificial Intelligence."
        prompt = PromptUtils.build_question_prompt(question, context)
        
        assert "What is AI?" in prompt
        assert "AI stands for Artificial Intelligence." in prompt
        assert "Context from knowledge base:" in prompt
        assert "Instructions:" in prompt
    
    def test_build_question_prompt_empty_context(self):
        """Test building question prompt with empty context."""
        question = "What is AI?"
        context = ""
        prompt = PromptUtils.build_question_prompt(question, context)
        
        assert "What is AI?" in prompt
        assert "Context from knowledge base:" in prompt
    
    def test_build_question_prompt_empty_question(self):
        """Test building question prompt with empty question."""
        question = ""
        context = "Some context here."
        prompt = PromptUtils.build_question_prompt(question, context)
        
        assert "Question: " in prompt
        assert "Some context here." in prompt
    
    def test_build_question_prompt_long_context(self):
        """Test building question prompt with long context."""
        question = "Explain this."
        context = "This is a very long context. " * 100
        prompt = PromptUtils.build_question_prompt(question, context)
        
        assert "Explain this." in prompt
        assert "This is a very long context." in prompt
    
    def test_build_question_prompt_instructions(self):
        """Test that all instructions are included in the prompt."""
        question = "Test question"
        context = "Test context"
        prompt = PromptUtils.build_question_prompt(question, context)
        
        # Check all 6 instructions are present
        assert "1." in prompt
        assert "2." in prompt
        assert "3." in prompt
        assert "4." in prompt
        assert "5." in prompt
        assert "6." in prompt
        
        # Check instruction content
        assert "Answer the question based primarily on the provided context" in prompt
        assert "If the context doesn't contain enough information, say so clearly" in prompt
        assert "Be concise but comprehensive in your answer" in prompt
        assert "If you reference specific information, try to indicate source urls" in prompt
        assert "If the question cannot be answered from the context" in prompt
        assert "You could add additional information from your own knowledge" in prompt
    
    def test_build_question_prompt_format(self):
        """Test the format of the generated prompt."""
        question = "Test?"
        context = "Context."
        prompt = PromptUtils.build_question_prompt(question, context)
        
        # Check structure
        assert prompt.startswith("You are a helpful AI assistant")
        assert prompt.endswith("Answer:")


class TestPromptUtilsIntegration:
    """Integration tests for PromptUtils."""
    
    def test_identify_and_question_prompts_different(self):
        """Test that identify and question prompts are different."""
        message = "Test message"
        identify_prompt = PromptUtils.build_identify_prompt(message)
        question_prompt = PromptUtils.build_question_prompt(message, "context")
        
        assert identify_prompt != question_prompt
    
    def test_prompts_are_strings(self):
        """Test that all prompts return strings."""
        identify_prompt = PromptUtils.build_identify_prompt("test")
        question_prompt = PromptUtils.build_question_prompt("test", "context")
        
        assert isinstance(identify_prompt, str)
        assert isinstance(question_prompt, str)
