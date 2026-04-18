"""Tests para geih.utils — Estadísticas ponderadas."""

import numpy as np
import pandas as pd
import pytest

from geih.utils import EstadisticasPonderadas as EP


class TestMedia:
    """Tests de media ponderada."""

    def test_pesos_iguales(self, df_simple):
        """Con pesos iguales, media ponderada = media aritmética."""
        resultado = EP.media(df_simple["valor"], df_simple["peso"])
        assert resultado == pytest.approx(300.0)

    def test_pesos_desiguales(self, df_pesos_desiguales):
        """Con peso 10 en valor 100, la media se sesga hacia 100."""
        resultado = EP.media(df_pesos_desiguales["valor"], df_pesos_desiguales["peso"])
        # (100*10 + 200*1 + 300*1) / (10+1+1) = 1500/12 = 125.0
        assert resultado == pytest.approx(125.0)

    def test_con_nans(self):
        """Los NaN se ignoran correctamente."""
        valores = pd.Series([100, np.nan, 300])
        pesos = pd.Series([1.0, 1.0, 1.0])
        resultado = EP.media(valores, pesos)
        assert resultado == pytest.approx(200.0)

    def test_pesos_cero(self):
        """Pesos = 0 se ignoran."""
        valores = pd.Series([100, 200])
        pesos = pd.Series([0.0, 0.0])
        assert np.isnan(EP.media(valores, pesos))

    def test_vacio(self):
        """Serie vacía retorna NaN."""
        assert np.isnan(EP.media(pd.Series(dtype=float), pd.Series(dtype=float)))


class TestMediana:
    """Tests de mediana ponderada."""

    def test_pesos_iguales(self, df_simple):
        """Con pesos iguales, mediana ponderada = mediana simple."""
        resultado = EP.mediana(df_simple["valor"], df_simple["peso"])
        assert resultado == pytest.approx(300.0)

    def test_pesos_desiguales(self, df_pesos_desiguales):
        """Con peso 10 en valor 100, la mediana se desplaza hacia 100."""
        resultado = EP.mediana(df_pesos_desiguales["valor"], df_pesos_desiguales["peso"])
        # 10/12 del peso está en 100, mediana debe ser 100
        assert resultado == pytest.approx(100.0)


class TestPercentil:
    """Tests de percentil ponderado."""

    def test_p0_es_minimo(self):
        """Percentil 0 debe ser el valor mínimo."""
        v = pd.Series([10, 20, 30, 40, 50])
        w = pd.Series([1.0] * 5)
        assert EP.percentil(v, w, 0.0) == pytest.approx(10.0)

    def test_p100_es_maximo(self):
        """Percentil 1.0 debe ser el valor máximo."""
        v = pd.Series([10, 20, 30, 40, 50])
        w = pd.Series([1.0] * 5)
        assert EP.percentil(v, w, 1.0) == pytest.approx(50.0)

    def test_p50_es_mediana(self):
        """Percentil 0.5 = mediana ponderada."""
        v = pd.Series([10, 20, 30])
        w = pd.Series([1.0, 1.0, 1.0])
        assert EP.percentil(v, w, 0.5) == EP.mediana(v, w)


class TestDesviacionEstandar:
    """Tests de desviación estándar ponderada."""

    def test_valores_iguales(self):
        """Todos iguales → desviación = 0."""
        v = pd.Series([100, 100, 100])
        w = pd.Series([1.0, 1.0, 1.0])
        assert EP.desviacion_estandar(v, w) == pytest.approx(0.0)

    def test_positiva(self, df_simple):
        """Con valores distintos, desviación > 0."""
        resultado = EP.desviacion_estandar(df_simple["valor"], df_simple["peso"])
        assert resultado > 0


class TestGini:
    """Tests del coeficiente de Gini."""

    def test_igualdad_perfecta(self):
        """Todos ganan igual → Gini ≈ 0."""
        v = pd.Series([1000] * 100)
        w = pd.Series([1.0] * 100)
        gini = EP.gini(v, w)
        assert gini == pytest.approx(0.0, abs=0.01)

    def test_desigualdad_alta(self):
        """Uno gana todo → Gini cercano a 1."""
        v = pd.Series([1] * 99 + [10_000])
        w = pd.Series([1.0] * 100)
        gini = EP.gini(v, w)
        assert gini > 0.9

    def test_rango_valido(self):
        """Gini siempre entre 0 y 1."""
        v = pd.Series(np.random.lognormal(10, 1, size=500))
        w = pd.Series(np.ones(500))
        gini = EP.gini(v, w)
        assert 0 <= gini <= 1

    def test_vacio_retorna_nan(self):
        """Con menos de 2 valores, retorna NaN."""
        assert np.isnan(EP.gini(pd.Series([100]), pd.Series([1.0])))


class TestResumenCompleto:
    """Tests de resumen_completo."""

    def test_retorna_dict(self, df_simple):
        """Debe retornar un diccionario con las claves esperadas."""
        resultado = EP.resumen_completo(df_simple["valor"], df_simple["peso"])
        assert "Media" in resultado
        assert "Mediana" in resultado
        assert "P10" in resultado
        assert "P90" in resultado
        assert "CV_%" in resultado
        assert "Media_SMMLV" in resultado

    def test_media_smmlv_correcto(self):
        """Media_SMMLV = Media / SMMLV."""
        v = pd.Series([1_423_500] * 10)
        w = pd.Series([1.0] * 10)
        resultado = EP.resumen_completo(v, w, smmlv=1_423_500)
        assert resultado["Media_SMMLV"] == pytest.approx(1.0)
