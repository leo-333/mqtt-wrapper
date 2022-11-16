import smtplib
import unittest
import utils
import python_jwt as create_jwt, jwcrypto.jwk as jwk, datetime
import jwt
import time


class MQTTWrapperTestCases(unittest.TestCase):
    def test_verify_jwt(self):
        # Test basic Verification
        payload = {'content': 'test'}
        key, token = generate_jwt(payload)

        self.assertEqual(utils.verify_jwt(token, key)['content'], payload['content'])

    def test_verify_invalid_jwt(self):
        # Test Invalid Signature
        with self.assertRaises(jwt.exceptions.InvalidSignatureError):
            payload = {'content': 'test'}
            key, token = generate_jwt(payload)
            token = token + 'a'
            utils.verify_jwt(token, key)

    def test_verify_expired_jwt(self):
        # Test Invalid Signature
        with self.assertRaises(jwt.exceptions.ExpiredSignatureError):
            payload = {'content': 'test'}
            key, token = generate_jwt(payload, lifetime=1)
            # wait for jwt to expire
            time.sleep(2)
            utils.verify_jwt(token, key)




    # def test_auth_email_auth_fail(self):
    #     with self.assertRaises(smtplib.SMTPAuthenticationError):
    #         main.send_auth_mail(
    #             auth_url='test',
    #             sender_email='asdf',
    #             receiver_email='asdf',
    #             smtp_proxy='smtp.gmail.com',
    #             smtp_port=123,
    #             smtp_password='asdf'
    #         )


def generate_jwt(payload, lifetime=500):
    key = jwk.JWK.generate(kty='RSA', size=2048)
    priv_pem = key.export_to_pem(private_key=True, password=None)
    pub_pem = key.export_to_pem()
    priv_key = jwk.JWK.from_pem(priv_pem)
    pub_key = jwk.JWK.from_pem(pub_pem)
    token = create_jwt.generate_jwt(payload, priv_key, 'RS256', datetime.timedelta(seconds=lifetime))

    return pub_key.export_to_pem(), token


if __name__ == "__main__":
    unittest.main()
