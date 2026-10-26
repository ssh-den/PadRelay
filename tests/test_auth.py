import pytest
from padrelay.security.auth import Authenticator


def test_tcp_response_roundtrip():
    auth = Authenticator('secret')
    challenge = 'abc123'
    response = auth.generate_tcp_response(challenge)
    assert auth.verify_tcp_response(challenge, response)
    assert not auth.verify_tcp_response(challenge, 'wrong')


def test_auth_without_password():
    auth = Authenticator(None)
    challenge = 'xyz'
    assert auth.verify_tcp_response(challenge, 'anything')
    assert auth.generate_tcp_response(challenge) == ''
    assert auth.generate_udp_token() is None
    assert auth.authenticate_udp({'type': 'input'})


def test_udp_token_authentication():
    auth = Authenticator('pass')
    token = auth.generate_udp_token(current_time=1000)
    assert auth.authenticate_udp({'auth_token': token}, current_time=1000)
    assert not auth.authenticate_udp({'auth_token': 'bad'}, current_time=1000)


def test_udp_token_rotation():
    auth = Authenticator('rot')
    t1 = 2000
    token1 = auth.generate_udp_token(current_time=t1)
    token2 = auth.generate_udp_token(current_time=t1 + auth.UDP_TOKEN_TTL + 1)
    assert token1 != token2
    assert auth.authenticate_udp({'auth_token': token1}, current_time=t1)
    # Old token should still be valid within one window
    assert auth.authenticate_udp({'auth_token': token1}, current_time=t1 + auth.UDP_TOKEN_TTL - 1)


def test_udp_token_expiration():
    auth = Authenticator('exp')
    start = 3000
    token = auth.generate_udp_token(current_time=start)
    # Token valid in same window
    assert auth.authenticate_udp({'auth_token': token}, current_time=start)
    # Token invalid after two windows
    assert not auth.authenticate_udp({'auth_token': token}, current_time=start + auth.UDP_TOKEN_TTL * 2)


def test_password_hash_roundtrip(tmp_path):
    hashed = Authenticator.hash_password('pw', iterations=100000)
    auth = Authenticator(hashed)
    assert auth.verify_password('pw')
    assert not auth.verify_password('bad')


def test_tcp_auth_with_hashed_server():
    hashed = Authenticator.hash_password('pw', iterations=120000)
    server = Authenticator(hashed)
    client = Authenticator('pw')
    client.set_parameters(server.salt, server.iterations)
    challenge = server.generate_tcp_challenge()
    response = client.generate_tcp_response(challenge)
    assert server.verify_tcp_response(challenge, response)
