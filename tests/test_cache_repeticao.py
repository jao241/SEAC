import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import chromadb
import numpy as np

from app.assistente import Cache, id_pergunta, responder


class ModeloFalso:
    def __init__(self, *args, **kwargs):
        pass

    def encode(self, texto, normalize_embeddings=True):
        return np.array([1.0, 0.0, 0.0])


class TestCache(unittest.TestCase):
    def test_perguntas_com_e_sem_acentos_sao_equivalentes(self):
        self.assertEqual(id_pergunta("Quem é você?"), id_pergunta("quem e voce"))

    def test_migracao_remove_historico_e_mantem_resposta(self):
        with tempfile.TemporaryDirectory() as diretorio:
            cliente = chromadb.PersistentClient(path=diretorio)
            with patch("chromadb.PersistentClient", return_value=cliente), \
                 patch("sentence_transformers.SentenceTransformer", ModeloFalso):
                from app.assistente import CONHECIMENTO, INSTRUCOES
                import hashlib
                import json
                versao = hashlib.sha256(
                    (json.dumps(CONHECIMENTO, sort_keys=True) + INSTRUCOES).encode()
                ).hexdigest()[:12]
                colecao = cliente.get_or_create_collection(
                    "conversas-" + versao, configuration={"hnsw": {"space": "cosine"}}
                )
                colecao.upsert(ids=["antigo"], embeddings=[[1.0, 0.0, 0.0]],
                               documents=["Quem é você?"],
                               metadatas=[{"historico": '[{"texto":"Olá"}]', "resposta": "Sou o assistente."}])
                cache = Cache()
                cache.inicializar()
                registros = colecao.get(include=["metadatas"])
                self.assertEqual(registros["ids"], [id_pergunta("quem e voce")])
                self.assertEqual(registros["metadatas"], [{"resposta": "Sou o assistente."}])
                self.assertEqual(cache.buscar("quem e voce")[0]["resposta"], "Sou o assistente.")
                cache.gravar("quem e voce", "Resposta atualizada.")
                self.assertEqual(colecao.count(), 1)
                self.assertEqual(cache.buscar("Quem é você?")[0]["resposta"], "Resposta atualizada.")


class TestFluxoCache(unittest.IsolatedAsyncioTestCase):
    async def test_correspondencia_retorna_sem_gemini_mesmo_com_termos_diferentes(self):
        candidato = {"pergunta": "Qual a capital do Japão?", "resposta": "Fora do domínio.", "distancia": 0.1}
        with patch("app.assistente.cache.executar", new=AsyncMock(return_value=[candidato])), \
             patch("app.assistente.genai.Client", side_effect=AssertionError("Chamou o Gemini")):
            self.assertEqual(await responder("Qual a capital japonesa?", []), ("Fora do domínio.", "cache"))

    async def test_sem_correspondencia_chama_llm_e_grava_resposta(self):
        llm = MagicMock()
        llm.aio.interactions.create = AsyncMock(return_value=MagicMock(steps=[], output_text="Resposta nova"))
        llm.aio.aclose = AsyncMock()
        with patch.dict("os.environ", {"GOOGLE_API_KEY": "teste"}), \
             patch("app.assistente.cache.executar", new=AsyncMock(side_effect=[[], None])) as executar, \
             patch("app.assistente.genai.Client", return_value=llm):
            self.assertEqual(await responder("Uma pergunta nova", []), ("Resposta nova", "llm"))
            self.assertEqual(executar.await_count, 2)
            llm.aio.interactions.create.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
