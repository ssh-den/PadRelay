from padrelay.security.auth import Authenticator


def test_tcp_response_roundtrip():
    auth = Authenticator("secret")
    challenge = "abc123"
    response = auth.generate_tcp_response(challenge)
    assert auth.verify_tcp_response(challenge, response)
    assert not auth.verify_tcp_response(challenge, "wrong")


def test_auth_without_password():
    auth = Authenticator(None)
    challenge = "xyz"
    assert auth.verify_tcp_response(challenge, "anything")
    assert auth.generate_tcp_response(challenge) == ""


def test_password_hash_roundtrip(tmp_path):
    hashed = Authenticator.hash_password("pw", iterations=100000)
    auth = Authenticator(hashed)
    assert auth.verify_password("pw")
    assert not auth.verify_password("bad")


def test_tcp_auth_with_hashed_server():
    hashed = Authenticator.hash_password("pw", iterations=120000)
    server = Authenticator(hashed)
    client = Authenticator("pw")
    client.set_parameters(server.salt, server.iterations)
    challenge = server.generate_tcp_challenge()
    response = client.generate_tcp_response(challenge)
    assert server.verify_tcp_response(challenge, response)
