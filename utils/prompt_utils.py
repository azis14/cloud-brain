class PromptUtils:
    """Utility class for prompt-related operations."""

    @staticmethod
    def build_identify_prompt(message: str) -> str:
        """Build the identify prompt for the AI model"""
        
        prompt = (
            "You are an AI assistant. Plese identify this message intention based on these options:\n\n"
            "1. 'QUERY'. If the message intent to ask question or try to get data from the knowledge base \n"
            "2. 'SYNC'. If the message intent to command the system sync data from the notion to pgvector \n"
            "3. 'UNKNOWN'. If you can't identify the intention of the message \n\n"
            f"Message: {message}\n\n"
            "Response with ONLY one of these option: 'QUERY', 'SYNC', 'UNKNOWN'."
        )
        
        return prompt
    
    @staticmethod
    def build_question_prompt(question: str, context: str) -> str:
        """Build the question prompt for the AI model"""
        
        prompt = f"""You are a helpful AI assistant that answers questions based on the provided context from a personal knowledge base. 

        Context from knowledge base:
        {context}

        Question: {question}

        Instructions:
        1. Answer the question based primarily on the provided context
        2. If the context doesn't contain enough information, say so clearly
        3. Be concise but comprehensive in your answer
        4. If you reference specific information, try to indicate source urls or page titles if available
        5. If the question cannot be answered from the context, explain what information would be needed
        6. You could add additional information from your own knowledge if it helps answer the question, but make it clear that this is additional context

        Answer:"""
        
        return prompt