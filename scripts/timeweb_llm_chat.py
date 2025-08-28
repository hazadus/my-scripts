#!/usr/bin/env -S uv run --quiet --script

# /// script
# dependencies = [
#   "requests",
#   "textual",
# ]
# ///
"""
Простейший чат-бот с TUI на основе LLM от Timeweb.
"""
import sys

import requests
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Footer, Header, Input, Static


class ChatApp(App):
    DEFAULT_CSS = """
    #messages {
        width: 100%;
        height: 1fr;
        background: $panel;
        border: tall $primary;
        padding: 1;
    }

    #message-input {
        height: 3;
    }

    .user-message {
        background: $primary-lighten-2;
        color: $text;
        margin: 1 0;
        padding: 1;
        text-style: bold;
    }

    .bot-message {
        background: $boost;
        color: $text;
        margin: 1 0;
        padding: 1;
    }
    """

    BINDINGS = [("d", "toggle_dark", "Переключить тему")]

    def __init__(
        self,
        agent_id: str,
        driver_class=None,
        css_path=None,
        watch_css=False,
        ansi_color=False,
    ):
        self.parent_message_id = None
        self.agent_id = agent_id
        super().__init__(driver_class, css_path, watch_css, ansi_color)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            VerticalScroll(id="messages"),
            Input(
                placeholder="Введите сообщение...",
                id="message-input",
            ),
        )
        yield Footer()

    @on(Input.Submitted)
    def handle_message_submitted(
        self,
        event: Input.Submitted,
    ) -> None:
        """Обработчик отправки сообщения из поля ввода."""
        message_text = event.value

        if message_text:
            message_container = self.query_one("#messages", VerticalScroll)
            user_message = Static(f"{message_text}", classes="user-message")
            message_container.mount(user_message)

            result = get_llm_answer(
                agent_id=self.agent_id,
                message=message_text,
                parent_message_id=self.parent_message_id,
            )
            bot_message = Static(f"{result["message"]}", classes="bot-message")
            message_container.mount(bot_message)
            self.parent_message_id = result["response_id"]

            # Очищаем поле ввода и прокручиваем вниз
            self.query_one("#message-input", Input).value = ""
            message_container.scroll_end(animate=True)

    def action_toggle_dark(self):
        if self.theme == "textual-dark":
            self.theme = "textual-light"
        else:
            self.theme = "textual-dark"


def get_llm_answer(
    *,
    agent_id: str,
    message: str,
    parent_message_id: str | None = None,
) -> dict:
    """
    Получить ответ от LLM.

    API Docs: https://agent.timeweb.cloud/docs#tag/ai-agents-client/post/api/v1/cloud-ai/agents/{agent_access_id}/call

    Args:
        agent_id (str): ID агента.
        message (str): Сообщение для отправки.
        parent_message_id (str | None): ID родительского сообщения (если есть).

    Returns:
        dict: Ответ от LLM.
    """
    response = requests.post(
        url=f"https://agent.timeweb.cloud/api/v1/cloud-ai/agents/{agent_id}/call",
        json={
            "message": message,
            "parent_message_id": parent_message_id,
        },
    )
    return response.json()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Использование: {sys.argv[0]} <agent_id>")
        sys.exit(1)

    agent_id = sys.argv[1]

    app = ChatApp(agent_id=agent_id)
    app.run()
