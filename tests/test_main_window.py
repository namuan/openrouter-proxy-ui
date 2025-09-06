# tests/test_main_window.py
import asyncio
import logging

import httpx
from PyQt6.QtCore import Qt

from proxy_interceptor.main_window import MainWindow

logger = logging.getLogger(__name__)


class TestMainWindow:
    """Test cases for the MainWindow class."""

    def _setup_window_and_verify_initial_state(self, qtbot):
        """Create window, show it, and verify basic properties."""
        # Create the main window
        window = MainWindow()

        # Add the window to qtbot for proper cleanup
        qtbot.addWidget(window)

        # Show the window
        with qtbot.waitExposed(window, timeout=1000):
            window.show()

        # Verify the window is visible
        assert window.isVisible()

        # Wait for proxy to start automatically
        qtbot.waitUntil(
            lambda: window.toggle_proxy_btn.text() == "Stop Proxy", timeout=5000
        )

        # Verify the window title
        assert window.windowTitle() == "OpenRouter Proxy Interceptor"

        # Verify the window has the expected size policy
        assert window.minimumSize().width() > 0
        assert window.minimumSize().height() > 0

        return window

    def _make_test_request(self):
        """Create an async HTTP request to the proxy server."""

        async def make_request():
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.post(
                        "http://127.0.0.1:8080/v1/chat/completions",
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": "Bearer dummy-key",
                        },
                        json={
                            "model": "it-doesnt-exist",
                            "messages": [{"role": "user", "content": "Hello"}],
                        },
                        timeout=10.0,
                    )
                    print(f"Request completed with status: {response.status_code}")
                    return response
                except Exception as e:
                    print(f"Request failed: {e}")
                    return None

        return make_request

    def _execute_async_request(self, async_request_func):
        """Execute an async request using a new event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(async_request_func())
        finally:
            loop.close()

    def _verify_request_in_list(self, window, qtbot):
        """Wait for and verify that the request appears in the list."""
        # Wait for the request to appear in the requests list
        qtbot.waitUntil(
            lambda: len(
                window.request_list_widget.request_list.findItems(
                    "POST /v1/chat/completions", Qt.MatchFlag.MatchContains
                )
            )
            > 0,
            timeout=5000,
        )

        # Verify the request is in the list
        items = window.request_list_widget.request_list.findItems(
            "POST /v1/chat/completions", Qt.MatchFlag.MatchContains
        )
        assert len(items) == 1
        request_item = items[0]
        assert "POST /v1/chat/completions" in request_item.text()

        return request_item

    def _select_request_and_verify_details(self, window, qtbot, request_item):
        """Select a request item and verify its details are populated."""
        list_widget = window.request_list_widget.request_list
        rect = list_widget.visualItemRect(request_item)
        qtbot.mouseClick(
            list_widget.viewport(), Qt.MouseButton.LeftButton, pos=rect.center()
        )

        # Wait until details are populated
        qtbot.waitUntil(
            lambda: window.request_details_widget.request_headers.toPlainText() != "",
            timeout=5000,
        )
        qtbot.waitUntil(
            lambda: window.request_details_widget.request_body.toPlainText() != "",
            timeout=5000,
        )

        # Verify request details
        req_headers_text = window.request_details_widget.request_headers.toPlainText()
        req_body_text = window.request_details_widget.request_body.toPlainText()
        assert req_headers_text != ""
        assert req_body_text != ""

        # Verify response details are populated
        resp_headers_text = window.request_details_widget.response_headers.toPlainText()
        resp_body_parsed_text = (
            window.request_details_widget.response_body_parsed.toPlainText()
        )
        assert resp_headers_text != ""
        assert resp_body_parsed_text != ""

    def _verify_response_tabs(self, window):
        """Test switching between Parsed and Raw response tabs."""
        # Switch to Raw tab and verify content
        window.request_details_widget.response_body_tabs.setCurrentIndex(1)
        resp_body_raw_text = (
            window.request_details_widget.response_body_raw.toPlainText()
        )
        assert resp_body_raw_text != ""

        # Switch back to Parsed tab and verify content remains
        window.request_details_widget.response_body_tabs.setCurrentIndex(0)
        assert window.request_details_widget.response_body_parsed.toPlainText() != ""

    def _toggle_proxy_and_verify_state(self, window, qtbot, expected_final_state):
        """Toggle proxy state and verify the button text and URL label."""
        if window.toggle_proxy_btn.text() == "Stop Proxy":
            qtbot.mouseClick(window.toggle_proxy_btn, Qt.MouseButton.LeftButton)
            qtbot.waitUntil(
                lambda: window.toggle_proxy_btn.text() == "Start Proxy", timeout=5000
            )
            # proxy_url_label should be disabled when stopped
            assert (
                not window.proxy_url_label.isEnabled()
                or "127.0.0.1" not in window.proxy_url_label.text()
            )

        if expected_final_state == "Stop Proxy":
            qtbot.mouseClick(window.toggle_proxy_btn, Qt.MouseButton.LeftButton)
            qtbot.waitUntil(
                lambda: window.toggle_proxy_btn.text() == "Stop Proxy", timeout=10000
            )

    def _find_clear_button(self, window):
        """Find the clear button in the main window."""
        clear_btn = None
        for btn in window.findChildren(type(window.toggle_proxy_btn)):
            try:
                if "clear" in btn.text().lower():
                    clear_btn = btn
                    break
            except Exception as e:
                logger.debug(f"Error finding clear button: {e}")
                continue

        assert clear_btn is not None, "Clear button not found in main window"
        return clear_btn

    def _clear_requests_and_verify(self, window, qtbot):
        """Clear all requests and verify the list is empty."""
        clear_btn = self._find_clear_button(window)
        qtbot.mouseClick(clear_btn, Qt.MouseButton.LeftButton)

        # Wait and check that there are no requests in list_widget
        list_widget = window.request_list_widget.request_list
        qtbot.waitUntil(lambda: list_widget.count() == 0, timeout=3000)
        assert list_widget.count() == 0

    def _find_configuration_tab(self, window):
        """Find and switch to the Configuration tab."""
        tab_widget = None
        config_tab_index = None
        from PyQt6.QtWidgets import QTabWidget

        for tw in window.findChildren(QTabWidget):
            # try to find a tab called "Configuration"
            for i in range(tw.count()):
                try:
                    if tw.tabText(i).lower() == "configuration":
                        tab_widget = tw
                        config_tab_index = i
                        break
                except Exception as e:
                    logger.debug(f"Error finding configuration tab: {e}")
                    continue
            if tab_widget:
                break

        assert (
            tab_widget is not None
        ), "Main tab widget with 'Configuration' tab not found"

        return tab_widget, config_tab_index

    def _switch_to_configuration_tab(self, window, qtbot):
        """Switch to the Configuration tab and verify basic content."""
        tab_widget, config_tab_index = self._find_configuration_tab(window)
        tab_widget.setCurrentIndex(config_tab_index)
        qtbot.waitUntil(
            lambda: tab_widget.currentIndex() == config_tab_index, timeout=2000
        )

        # Verify that there is data in OpenRouter API Keys input widget
        cfg = window.config_widget
        api_keys_text = cfg.api_keys_text.toPlainText()
        assert isinstance(api_keys_text, str)

        # Verify that there are items in OpenRouter free models
        free_models = cfg.model_selection_widget.free_models
        assert isinstance(free_models, list)
        assert free_models is not None

        return cfg

    def _test_port_change(self, window, qtbot, cfg):
        """Test changing the server port and verifying the changes."""
        # Get original port
        original_port_text = cfg.port_input.text()
        assert original_port_text != ""

        # Update server port (use a different port)
        try:
            new_port = str(int(original_port_text) + 1)
        except Exception:
            new_port = "8081"

        # Change port and save configuration
        cfg.port_input.setText(new_port)
        if hasattr(cfg, "save_btn"):
            qtbot.mouseClick(cfg.save_btn, Qt.MouseButton.LeftButton)

        # Start proxy again to pick up new port
        qtbot.mouseClick(window.toggle_proxy_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(
            lambda: window.toggle_proxy_btn.text() == "Stop Proxy", timeout=10000
        )

        # Wait until proxy_url_label shows new port
        qtbot.waitUntil(
            lambda: f":{new_port}" in window.proxy_url_label.text(), timeout=5000
        )
        assert f":{new_port}" in window.proxy_url_label.text()

        return original_port_text, new_port

    def _revert_port_change(self, window, qtbot, cfg, original_port_text):
        """Revert the port back to original and restart proxy."""
        # Stop proxy, revert port, save and restart proxy to restore original state
        qtbot.mouseClick(window.toggle_proxy_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(
            lambda: window.toggle_proxy_btn.text() == "Start Proxy", timeout=5000
        )

        cfg.port_input.setText(original_port_text)
        if hasattr(cfg, "save_btn"):
            qtbot.mouseClick(cfg.save_btn, Qt.MouseButton.LeftButton)

        # Start proxy back
        qtbot.mouseClick(window.toggle_proxy_btn, Qt.MouseButton.LeftButton)
        qtbot.waitUntil(
            lambda: window.toggle_proxy_btn.text() == "Stop Proxy", timeout=10000
        )
        qtbot.waitUntil(
            lambda: f":{original_port_text}" in window.proxy_url_label.text(),
            timeout=5000,
        )
        assert f":{original_port_text}" in window.proxy_url_label.text()

    def test_e2e(self, qtbot):
        """End-to-end test of the main window functionality."""
        # 1. Setup window and verify initial state
        window = self._setup_window_and_verify_initial_state(qtbot)

        # 2. Make HTTP request and execute it
        async_request = self._make_test_request()
        self._execute_async_request(async_request)

        # 3. Verify request appears in list and select it
        request_item = self._verify_request_in_list(window, qtbot)
        self._select_request_and_verify_details(window, qtbot, request_item)

        # 4. Test response tabs functionality
        self._verify_response_tabs(window)

        # 5. Test proxy toggle functionality
        self._toggle_proxy_and_verify_state(window, qtbot, "Start Proxy")

        # 6. Test clear requests functionality
        self._clear_requests_and_verify(window, qtbot)

        # 7. Test configuration tab functionality
        cfg = self._switch_to_configuration_tab(window, qtbot)

        # 8. Test port change functionality
        original_port_text, new_port = self._test_port_change(window, qtbot, cfg)

        # 9. Revert port changes to restore original state
        self._revert_port_change(window, qtbot, cfg, original_port_text)

        # Final wait
        qtbot.wait(200)
