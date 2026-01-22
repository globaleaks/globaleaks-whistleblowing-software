import json
from unittest.mock import Mock, patch, MagicMock
from twisted.trial import unittest
from twisted.internet import reactor, defer
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.test.proto_helpers import StringTransport
from globaleaks.tests.helpers import TestGL, TestGLWithPopulatedDB, USER_PRV_KEY
from globaleaks.sessions import Sessions
from globaleaks.orm import tw
from globaleaks.utils.websocket_server import GLWebSocketProtocol, WebSocketServerFactory, CLIENTS, start_ws_server, notify_users


class TestWebSocketProtocol(TestGL):
    @inlineCallbacks
    def setUp(self):
        yield TestGL.setUp(self)
        
        # Initialize WebSocket factory
        self.factory = WebSocketServerFactory("ws://127.0.0.1:9000")
        self.factory.protocol = GLWebSocketProtocol
        
        # Clear global clients set
        CLIENTS.clear()
        
        # Create a test session
        self.session_id = "test_session_123"
        self.user_id = "test_user_456"
        self.tip_ids = ["tip_1", "tip_2"]
        
        # Mock session in Sessions
        self.mock_session = Mock()
        self.mock_session.user_id = self.user_id
        # Save original sessions and restore in tearDown
        self.original_sessions = getattr(Sessions, '_sessions', {})
        Sessions._sessions = {self.session_id: self.mock_session}
    
    def tearDown(self):
        # Restore original sessions
        if hasattr(self, 'original_sessions'):
            Sessions._sessions = self.original_sessions
        super().tearDown()
    
    def create_mock_protocol(self):
        """Create a mock protocol instance for testing"""
        protocol = GLWebSocketProtocol()
        protocol.factory = self.factory
        protocol.transport = StringTransport()
        protocol.peer = Mock()
        # Initialize attributes manually since they're not in __init__
        protocol.user_id = None
        protocol.tip_ids = set()
        protocol.session = None
        return protocol
    
    def test_on_open_adds_client_to_global_set(self):
        """Test that onOpen adds client to CLIENTS set"""
        protocol = self.create_mock_protocol()
        
        # Initial state
        self.assertEqual(len(CLIENTS), 0)
        self.assertIsNone(protocol.user_id)
        self.assertEqual(protocol.tip_ids, set())
        self.assertIsNone(protocol.session)
        
        # Call onOpen
        protocol.onOpen()
        
        # Verify client was added
        self.assertEqual(len(CLIENTS), 1)
        self.assertIn(protocol, CLIENTS)
        
        # Verify initial protocol state
        self.assertIsNone(protocol.user_id)
        self.assertEqual(protocol.tip_ids, set())
        self.assertIsNone(protocol.session)
    
    def test_on_close_removes_client_from_global_set(self):
        """Test that onClose removes client from CLIENTS set"""
        protocol = self.create_mock_protocol()
        
        # Add client to set
        protocol.onOpen()
        self.assertEqual(len(CLIENTS), 1)
        
        # Call onClose
        protocol.onClose(True, 1000, "Normal closure")
        
        # Verify client was removed
        self.assertEqual(len(CLIENTS), 0)
        self.assertNotIn(protocol, CLIENTS)
    
    def test_on_message_with_invalid_json(self):
        """Test that invalid JSON sends close message"""
        protocol = self.create_mock_protocol()
        protocol.onOpen()
        protocol.sendClose = Mock()
        
        # Send invalid JSON
        protocol.onMessage(b"invalid json", False)
        
        # Verify close was called with error code
        protocol.sendClose.assert_called_once_with(code=4000, reason="Invalid JSON")
    
    def test_on_message_auth_without_session_id(self):
        """Test auth without session_id sends close message"""
        protocol = self.create_mock_protocol()
        protocol.onOpen()
        protocol.sendClose = Mock()
        
        # Send auth without session_id
        auth_msg = json.dumps({"type": "auth"}).encode("utf-8")
        protocol.onMessage(auth_msg, False)
        
        # Verify close was called
        protocol.sendClose.assert_called_once_with(code=4001, reason="Missing session_id")
    
    def test_on_message_auth_with_invalid_session(self):
        """Test auth with invalid session sends close message"""
        protocol = self.create_mock_protocol()
        protocol.onOpen()
        protocol.sendClose = Mock()
        
        # Send auth with invalid session_id
        auth_msg = json.dumps({
            "type": "auth",
            "session_id": "invalid_session"
        }).encode("utf-8")
        protocol.onMessage(auth_msg, False)
        
        # Verify close was called
        protocol.sendClose.assert_called_once_with(code=4002, reason="Invalid session")
    
    def test_on_message_successful_auth(self):
        """Test successful authentication"""
        protocol = self.create_mock_protocol()
        protocol.onOpen()
        protocol.sendClose = Mock()
        protocol.send_update = Mock()
        
        # Need to mock Sessions.get since the protocol uses it
        with patch.object(Sessions, 'get', return_value=self.mock_session) as mock_get:
            # Send valid auth message
            auth_msg = json.dumps({
                "type": "auth",
                "session_id": self.session_id,
                "tip_ids": self.tip_ids
            }).encode("utf-8")
            protocol.onMessage(auth_msg, False)
            
            # Verify Sessions.get was called
            mock_get.assert_called_once_with(self.session_id)
        
        # Verify session was set
        self.assertEqual(protocol.session, self.mock_session)
        self.assertEqual(protocol.user_id, self.user_id)
        self.assertEqual(protocol.tip_ids, set(self.tip_ids))
        
        # Verify auth_ok was sent
        protocol.send_update.assert_called_once_with({"type": "auth_ok"})
        
        # Verify close was not called
        protocol.sendClose.assert_not_called()
    
    def test_on_message_unknown_type(self):
        """Test message with unknown type is ignored"""
        protocol = self.create_mock_protocol()
        protocol.onOpen()
        protocol.sendClose = Mock()
        
        # Send message with unknown type
        unknown_msg = json.dumps({
            "type": "unknown_type",
            "data": "some data"
        }).encode("utf-8")
        protocol.onMessage(unknown_msg, False)
        
        # Verify close was not called
        protocol.sendClose.assert_not_called()
    
    def test_send_update(self):
        """Test send_update encodes and sends message"""
        protocol = self.create_mock_protocol()
        protocol.onOpen()
        protocol.sendMessage = Mock()
        
        # Create test payload
        payload = {
            "type": "notification",
            "data": "test notification"
        }
        
        # Call send_update
        protocol.send_update(payload)
        
        # Verify sendMessage was called with encoded JSON
        expected_message = json.dumps(payload).encode("utf-8")
        protocol.sendMessage.assert_called_once_with(expected_message)


class TestNotifyUsers(TestGL):
    @inlineCallbacks
    def setUp(self):
        yield TestGL.setUp(self)
        
        # Clear global clients set
        CLIENTS.clear()
        
        # Create mock clients
        self.client1 = Mock()
        self.client1.user_id = "user1"
        self.client1.tip_ids = {"tip1", "tip2"}
        self.client1.session = Mock()
        self.client1.send_update = Mock()
        
        self.client2 = Mock()
        self.client2.user_id = "user2"
        self.client2.tip_ids = {"tip2", "tip3"}
        self.client2.session = Mock()
        self.client2.send_update = Mock()
        
        self.client3 = Mock()
        self.client3.user_id = "user3"
        self.client3.tip_ids = {"tip3"}
        self.client3.session = Mock()
        self.client3.send_update = Mock()
        
        # Client without session (not authenticated)
        self.client4 = Mock()
        self.client4.user_id = None
        self.client4.tip_ids = set()
        self.client4.session = None
        self.client4.send_update = Mock()
        
        # Add clients to global set
        CLIENTS.update([self.client1, self.client2, self.client3, self.client4])
    
    def tearDown(self):
        # Clear CLIENTS after each test
        CLIENTS.clear()
        super().tearDown()
    
    def test_notify_users_without_filters(self):
        """Test notify_users sends to all authenticated clients"""
        payload = {"type": "broadcast", "message": "Hello everyone"}
        
        # Mock reactor.callFromThread to execute immediately
        with patch.object(reactor, 'callFromThread') as mock_call:
            def execute_immediately(func, *args, **kwargs):
                func(*args, **kwargs)
            mock_call.side_effect = execute_immediately
            
            # Call notify_users
            notify_users(payload)
        
        # Verify only authenticated clients received the message
        self.client1.send_update.assert_called_once_with(payload)
        self.client2.send_update.assert_called_once_with(payload)
        self.client3.send_update.assert_called_once_with(payload)
        self.client4.send_update.assert_not_called()  # No session
    
    def test_notify_users_with_user_ids_filter(self):
        """Test notify_users filters by user_ids"""
        payload = {"type": "private", "message": "Private message"}
        
        with patch.object(reactor, 'callFromThread') as mock_call:
            def execute_immediately(func, *args, **kwargs):
                func(*args, **kwargs)
            mock_call.side_effect = execute_immediately
            
            # Notify only user1 and user2
            notify_users(payload, user_ids=["user1", "user2"])
        
        # Verify only specified users received the message
        self.client1.send_update.assert_called_once_with(payload)
        self.client2.send_update.assert_called_once_with(payload)
        self.client3.send_update.assert_not_called()
        self.client4.send_update.assert_not_called()
    
    def test_notify_users_with_tip_id_filter(self):
        """Test notify_users filters by tip_id"""
        payload = {"type": "tip_update", "tip_id": "tip2"}
        
        with patch.object(reactor, 'callFromThread') as mock_call:
            def execute_immediately(func, *args, **kwargs):
                func(*args, **kwargs)
            mock_call.side_effect = execute_immediately
            
            # Notify clients subscribed to tip2
            notify_users(payload, tip_id="tip2")
        
        # Verify only clients with tip2 received the message
        self.client1.send_update.assert_called_once_with(payload)
        self.client2.send_update.assert_called_once_with(payload)
        self.client3.send_update.assert_not_called()  # Doesn't have tip2
        self.client4.send_update.assert_not_called()
    
    def test_notify_users_with_exclude_user(self):
        """Test notify_users excludes specific user"""
        payload = {"type": "notification", "message": "Everyone except user1"}
        
        with patch.object(reactor, 'callFromThread') as mock_call:
            def execute_immediately(func, *args, **kwargs):
                func(*args, **kwargs)
            mock_call.side_effect = execute_immediately
            
            # Notify everyone except user1
            notify_users(payload, exclude_user="user1")
        
        # Verify user1 was excluded
        self.client1.send_update.assert_not_called()
        self.client2.send_update.assert_called_once_with(payload)
        self.client3.send_update.assert_called_once_with(payload)
        self.client4.send_update.assert_not_called()
    
    def test_notify_users_with_multiple_filters(self):
        """Test notify_users with combined filters"""
        payload = {"type": "complex", "data": "complex notification"}
        
        with patch.object(reactor, 'callFromThread') as mock_call:
            def execute_immediately(func, *args, **kwargs):
                func(*args, **kwargs)
            mock_call.side_effect = execute_immediately
            
            # Notify user1 and user2 who have tip2, but exclude user1
            notify_users(payload, tip_id="tip2", user_ids=["user1", "user2"], exclude_user="user1")
        
        # Verify only user2 received the message (has tip2, in user_ids, not excluded)
        self.client1.send_update.assert_not_called()
        self.client2.send_update.assert_called_once_with(payload)
        self.client3.send_update.assert_not_called()
        self.client4.send_update.assert_not_called()
    
    def test_notify_users_empty_filters_match_all(self):
        """Test notify_users with empty filter lists matches all authenticated clients"""
        payload = {"type": "test", "data": "test"}
        
        with patch.object(reactor, 'callFromThread') as mock_call:
            def execute_immediately(func, *args, **kwargs):
                func(*args, **kwargs)
            mock_call.side_effect = execute_immediately
            
            # Empty user_ids list should match all users
            notify_users(payload, user_ids=[])
        
        # All authenticated clients should receive the message
        self.client1.send_update.assert_called_once_with(payload)
        self.client2.send_update.assert_called_once_with(payload)
        self.client3.send_update.assert_called_once_with(payload)
        self.client4.send_update.assert_not_called()


class TestWebSocketIntegration(TestGLWithPopulatedDB):
    @inlineCallbacks
    def setUp(self):
        yield TestGLWithPopulatedDB.setUp(self)
        
        # Clear global clients set
        CLIENTS.clear()
        
        # Perform a submission to get a real session
        yield self.perform_minimal_submission_actions()
        
        # Get the wbtip to have a real tip_id
        self.wbtips = yield self.get_wbtips()
        self.tip_id = self.wbtips[0]['id'] if self.wbtips else "test_tip"
    
    def tearDown(self):
        # Clear CLIENTS after each test
        CLIENTS.clear()
        super().tearDown()
    
    @inlineCallbacks
    def test_real_session_authentication(self):
        """Test WebSocket authentication with a real session"""
        # Create a real session for a receiver
        session = Sessions.new(1, self.dummyReceiver_1['id'], 1, 'receiver', USER_PRV_KEY, '', ['receiver'])
        
        protocol = GLWebSocketProtocol()
        protocol.onOpen()
        protocol.send_update = Mock()
        
        # Get the session dict from Sessions.get() to compare
        session_dict = Sessions.get(session.id)
        
        # Authenticate with real session
        auth_msg = json.dumps({
            "type": "auth",
            "session_id": session.id,
            "tip_ids": [self.tip_id]
        }).encode("utf-8")
        
        protocol.onMessage(auth_msg, False)
        
        # Verify authentication succeeded
        protocol.send_update.assert_called_once_with({"type": "auth_ok"})
        self.assertEqual(protocol.user_id, self.dummyReceiver_1['id'])
        self.assertEqual(protocol.tip_ids, {self.tip_id})
        
        # Check that session is set (don't compare exact objects, just check it's not None)
        self.assertIsNotNone(protocol.session)
        
        # Check that the session has the expected user_id
        self.assertEqual(protocol.session.user_id, self.dummyReceiver_1['id'])
        
        yield returnValue(None)
    
    @inlineCallbacks 
    def test_notify_specific_receiver_about_tip(self):
        """Test notification to specific receiver about their tip"""
        # Create authenticated clients
        protocol1 = GLWebSocketProtocol()
        protocol1.onOpen()
        # Initialize attributes
        protocol1.user_id = self.dummyReceiver_1['id']
        protocol1.tip_ids = {self.tip_id}
        protocol1.session = Mock()
        protocol1.send_update = Mock()
        
        protocol2 = GLWebSocketProtocol()
        protocol2.onOpen()
        # Initialize attributes
        protocol2.user_id = self.dummyReceiver_2['id']
        protocol2.tip_ids = set()  # No tips
        protocol2.session = Mock()
        protocol2.send_update = Mock()
        
        CLIENTS.update([protocol1, protocol2])
        
        # Notify about tip update
        payload = {"type": "tip_update", "tip_id": self.tip_id, "action": "new_comment"}
        
        with patch.object(reactor, 'callFromThread') as mock_call:
            def execute_immediately(func, *args, **kwargs):
                func(*args, **kwargs)
            mock_call.side_effect = execute_immediately
            
            notify_users(payload, tip_id=self.tip_id)
        
        # Verify only protocol1 (has the tip) received notification
        protocol1.send_update.assert_called_once_with(payload)
        protocol2.send_update.assert_not_called()
        yield returnValue(None)


class TestWebSocketEdgeCases(TestGL):
    @inlineCallbacks
    def setUp(self):
        yield TestGL.setUp(self)
        # Clear CLIENTS set
        CLIENTS.clear()
    
    def tearDown(self):
        # Clear CLIENTS after each test
        CLIENTS.clear()
        super().tearDown()
    
    def test_multiple_clients_same_user(self):
        """Test multiple WebSocket connections for same user"""
        # Clear any existing clients
        CLIENTS.clear()
        
        # Create two clients for the same user
        client1 = Mock()
        client1.user_id = "user1"
        client1.tip_ids = {"tip1"}
        client1.session = Mock()
        client1.send_update = Mock()
        
        client2 = Mock()
        client2.user_id = "user1"  # Same user
        client2.tip_ids = {"tip1"}
        client2.session = Mock()
        client2.send_update = Mock()
        
        CLIENTS.update([client1, client2])
        
        payload = {"type": "notification", "user": "user1"}
        
        with patch.object(reactor, 'callFromThread') as mock_call:
            def execute_immediately(func, *args, **kwargs):
                func(*args, **kwargs)
            mock_call.side_effect = execute_immediately
            
            notify_users(payload, user_ids=["user1"])
        
        # Both clients should receive the notification
        client1.send_update.assert_called_once_with(payload)
        client2.send_update.assert_called_once_with(payload)
    
    def test_client_without_tip_ids(self):
        """Test client with empty tip_ids"""
        # Clear any existing clients
        CLIENTS.clear()
        
        client = Mock()
        client.user_id = "user1"
        client.tip_ids = set()  # Empty set
        client.session = Mock()
        client.send_update = Mock()
        
        CLIENTS.update([client])
        
        payload = {"type": "tip_update", "tip_id": "tip1"}
        
        with patch.object(reactor, 'callFromThread') as mock_call:
            def execute_immediately(func, *args, **kwargs):
                func(*args, **kwargs)
            mock_call.side_effect = execute_immediately
            
            notify_users(payload, tip_id="tip1")
        
        # Client should not receive notification (empty tip_ids)
        client.send_update.assert_not_called()
    
    def test_notify_after_client_disconnect(self):
        """Test notification after client has disconnected"""
        # Clear any existing clients
        CLIENTS.clear()
        
        client = Mock()
        client.user_id = "user1"
        client.tip_ids = {"tip1"}
        client.session = Mock()
        client.send_update = Mock()
        
        # Add then remove client
        CLIENTS.add(client)
        self.assertEqual(len(CLIENTS), 1)
        
        CLIENTS.discard(client)
        self.assertEqual(len(CLIENTS), 0)
        
        payload = {"type": "notification"}
        
        with patch.object(reactor, 'callFromThread') as mock_call:
            def execute_immediately(func, *args, **kwargs):
                func(*args, **kwargs)
            mock_call.side_effect = execute_immediately
            
            notify_users(payload)
        
        # No notification should be sent to disconnected client
        client.send_update.assert_not_called()


class TestWebSocketServerStart(TestGL):
    def test_server_start(self):
        """Test that server can be started"""
        # Mock reactor.listenTCP to avoid actually starting server
        with patch.object(reactor, 'listenTCP') as mock_listen:
            start_ws_server()
            
            # Verify listenTCP was called with correct parameters
            # We can't use Mock() as the second argument since the factory is created inside start_ws_server
            mock_listen.assert_called_once()
            args, kwargs = mock_listen.call_args
            self.assertEqual(args[0], 9000)
            self.assertIsInstance(args[1], WebSocketServerFactory)