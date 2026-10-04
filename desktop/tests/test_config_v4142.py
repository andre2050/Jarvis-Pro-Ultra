import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

class V4142(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        import core.config as c
        c.CONFIG_DIR = Path(self.tmp)
        c.CONFIG_FILE = Path(self.tmp) / "config.json"
        self.c = c

    def test_defaults_novos(self):
        cfg = self.c.load()
        self.assertEqual(cfg["tools_desligadas"], [])
        self.assertEqual(cfg["atalho_voz"], "<F4>")
        self.assertFalse(cfg["economia_auto"])
        self.assertEqual(cfg["economia_bateria"], 40)

    def test_agenda_editar(self):
        from core import agenda
        agenda.CONFIG_DIR = Path(self.tmp)
        agenda.AGENDA_FILE = Path(self.tmp) / "agenda.json"
        msg = agenda.agendar("23:59", "teste edição")
        self.assertIn("senhor", msg)
        itens = agenda.itens()
        self.assertEqual(len(itens), 1)
        ident = itens[0]["id"]
        # editar motivo e horário
        r = agenda.editar(ident, "22:30", "motivo novo")
        self.assertIn("motivo novo", r)
        itens = agenda.itens()
        self.assertEqual(itens[0]["motivo"], "motivo novo")
        self.assertIn("22:30", itens[0]["quando"])
        # horário vazio mantém; motivo vazio mantém
        antes = itens[0]["quando"]
        agenda.editar(ident, "", "")
        itens = agenda.itens()
        self.assertEqual(itens[0]["quando"], antes)
        self.assertEqual(itens[0]["motivo"], "motivo novo")
        # horário inválido devolve erro claro
        r = agenda.editar(ident, "banana", "x")
        self.assertIn("não entendi", r)
        # id inexistente
        r = agenda.editar(999, "10:00", "x")
        self.assertIn("não encontrei", r)

    def test_gate_tools(self):
        from core import brain
        cfg = self.c.load()
        cfg["tools_desligadas"] = ["controlar_volume"]
        self.c.save(cfg)
        # a declaração some do catálogo do modelo
        nomes_decl = [d["name"] for d in brain.todas_declaracoes()]
        self.assertNotIn("controlar_volume", nomes_decl)
        self.assertIn("hora_agora", nomes_decl)
        # e a execução direta recusa na cara
        r = brain._executa_raw("controlar_volume", {})
        self.assertIn("desligada", r)
        r = brain._executa_raw("hora_agora", {})
        self.assertNotIn("desligada", r)

    def test_deps_status(self):
        from core import deps
        res = deps.status()
        self.assertGreaterEqual(len(res), 10)
        for r in res:
            for k in ("chave", "rotulo", "pip", "para", "ok", "motivo"):
                self.assertIn(k, r)
        # no sandbox psutil e requests estão instalados de verdade
        por = {r["chave"]: r for r in res}
        self.assertTrue(por["psutil"]["ok"])
        self.assertTrue(por["requests"]["ok"])

if __name__ == "__main__":
    unittest.main()
