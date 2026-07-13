import re
import unittest

from app import crear_app


class SmokeTestCase(unittest.TestCase):
    def setUp(self):
        self.app = crear_app()
        self.client = self.app.test_client()

    def test_home_loads_with_security_headers(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("X-Frame-Options"), "DENY")
        self.assertTrue(response.headers.get("Content-Security-Policy"))

    def test_post_without_csrf_is_rejected(self):
        response = self.client.post("/nuevo_activo", data={"num_activo": "TEST"})

        self.assertEqual(response.status_code, 400)

    def test_report_page_has_csrf_token(self):
        response = self.client.get("/reporte")

        self.assertEqual(response.status_code, 200)
        self.assertRegex(response.data, re.compile(rb'name="_csrf_token" value="[^"]+"'))


if __name__ == "__main__":
    unittest.main()
