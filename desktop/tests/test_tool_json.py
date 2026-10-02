"""Testes do leitor de JSON de ferramentas — port do LocalCommandParserTest
do Android v4.10.3. Rode:  python -m unittest discover tests -v"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import ollama_client  # noqa: E402

NOMES = {"lanterna", "hora_data", "teste"}


class ExtrairToolJsonTest(unittest.TestCase):
    def chama(self, texto):
        return ollama_client.extrair_tool_json(texto, NOMES)

    def test_args_aninhados(self):
        r = self.chama('{"tool":"lanterna","args":{"ligar":true}}')
        self.assertEqual(r["name"], "lanterna")
        self.assertIs(r["args"]["ligar"], True)

    def test_objetos_e_listas_aninhadas(self):
        r = self.chama('{"tool":"teste","args":{"config":{"n":2},"items":[{"x":1}]}}')
        self.assertEqual(r["args"]["config"]["n"], 2)
        self.assertEqual(r["args"]["items"][0]["x"], 1)

    def test_bloco_de_codigo(self):
        r = self.chama('```json\n{"tool":"hora_data","args":{}}\n```')
        self.assertEqual(r["name"], "hora_data")

    def test_chaves_aspas_e_escapes(self):
        r = self.chama('{"tool":"teste","args":{"texto":"{ok} \\"oi\\" C:\\\\tmp"}}')
        self.assertEqual(r["args"]["texto"], '{ok} "oi" C:\\tmp')

    def test_texto_antes_e_objetos_sem_tool(self):
        r = self.chama('Texto {"resposta":"ok"} {"tool":"hora_data"}')
        self.assertEqual(r["name"], "hora_data")

    def test_json_incompleto_e_recusado(self):
        self.assertIsNone(self.chama('{"tool":"lanterna","args":{"ligar":true}'))

    def test_args_invalidos_recusados(self):
        for args in ("null", "[]", "true", '"texto"', "5"):
            self.assertIsNone(self.chama('{"tool":"lanterna","args":%s}' % args))

    def test_nome_invalido_recusado(self):
        self.assertIsNone(self.chama('{"tool":null,"args":{}}'))
        self.assertIsNone(self.chama('{"tool":42,"args":{}}'))
        self.assertIsNone(self.chama('{"tool":"","args":{}}'))
        self.assertIsNone(self.chama('{"tool":"  ","args":{}}'))

    def test_resposta_pura_nao_e_comando(self):
        self.assertIsNone(self.chama('{"resposta":"Bom dia, senhor."}'))

    def test_sem_args_vira_objeto_vazio(self):
        r = self.chama('{"tool":"hora_data"}')
        self.assertEqual(r["name"], "hora_data")
        self.assertEqual(r["args"], {})

    def test_tool_desconhecida_recusada(self):
        self.assertIsNone(self.chama('{"tool":"abrir_nave","args":{}}'))


if __name__ == "__main__":
    unittest.main()
