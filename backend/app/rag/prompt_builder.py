"""
Grounded Prompt Builder

This module builds the final grounded prompt that is sent to the
Large Language Model (Gemini).

The PromptBuilder performs deterministic prompt construction only.

Responsibilities:
- Combine the user question with retrieved context.
- Apply a consistent prompt template.
- Produce a prompt-ready string for the LLM.

It does NOT:
- retrieve documents
- rewrite queries
- generate embeddings
- call Gemini
- generate answers
"""

from textwrap import dedent


GROUNDED_PROMPT_TEMPLATE = dedent(
    """
    You are an AI Knowledge Assistant.

    Your task is to answer the user's question ONLY using the provided context.

    Instructions:

    - Use only the information contained in the context.
    - Do not use outside knowledge.
    - Do not invent or assume missing information.
    - If the answer cannot be found in the context, respond with:
      "The requested information is not available in the uploaded documents."
    - Keep the answer clear, accurate, and concise.

    Context
    =======
    {context}

    Question
    ========
    {question}

    Answer:
    """
).strip()


NO_CONTEXT_PROMPT_TEMPLATE = dedent(
    """
    You are an AI Knowledge Assistant.

    No relevant document context was retrieved for the user's question.

    Respond ONLY with:

    "The requested information is not available in the uploaded documents."

    Question
    ========
    {question}

    Answer:
    """
).strip()


class PromptBuilder:
    """
    Builds the grounded prompt sent to the LLM.

    This class is deterministic. Given the same question and
    context, it always produces the same prompt.
    """

    def build_prompt(
        self,
        question: str,
        context: str,
    ) -> str:
        """
        Build the final prompt for Gemini.

        Args:
            question:
                Original user question.

            context:
                Structured context produced by ContextBuilder.

        Returns:
            Prompt string ready to send to Gemini.
        """

        question = question.strip()

        if not question:
            raise ValueError(
                "Question cannot be empty."
            )

        context = context.strip()

        if not context:
            return NO_CONTEXT_PROMPT_TEMPLATE.format(
                question=question,
            )

        return GROUNDED_PROMPT_TEMPLATE.format(
            context=context,
            question=question,
        )