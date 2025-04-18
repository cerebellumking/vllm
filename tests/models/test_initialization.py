# SPDX-License-Identifier: Apache-2.0

from unittest.mock import patch

import pytest
from transformers import PretrainedConfig

from vllm import LLM
from vllm.engine.llm_engine import LLMEngine as V0LLMEngine
from vllm.v1.engine.core import EngineCore as V1EngineCore

from .registry import HF_EXAMPLE_MODELS


@pytest.mark.parametrize("model_arch", HF_EXAMPLE_MODELS.get_supported_archs())
def test_can_initialize(model_arch):
    model_info = HF_EXAMPLE_MODELS.get_hf_info(model_arch)
    model_info.check_available_online(on_fail="skip")
    model_info.check_transformers_version(on_fail="skip")

    # Avoid OOM
    def hf_overrides(hf_config: PretrainedConfig) -> PretrainedConfig:
        hf_config.update(model_info.hf_overrides)

        if hasattr(hf_config, "text_config"):
            text_config: PretrainedConfig = hf_config.text_config
        else:
            text_config = hf_config

        text_config.update({
            "num_layers": 1,
            "num_hidden_layers": 1,
            "num_experts": 2,
            "num_experts_per_tok": 2,
            "num_local_experts": 2,
        })

        return hf_config

    # Avoid calling model.forward()
    def _initialize_kv_caches_v0(self) -> None:
        self.cache_config.num_gpu_blocks = 0
        self.cache_config.num_cpu_blocks = 0

    def _initalize_kv_caches_v1(self, vllm_config):
        # gpu_blocks (> 0), cpu_blocks
        return 1, 0

    with (patch.object(V0LLMEngine, "_initialize_kv_caches",
                       _initialize_kv_caches_v0),
          patch.object(V1EngineCore, "_initialize_kv_caches",
                       _initalize_kv_caches_v1)):
        LLM(
            model_info.default,
            tokenizer=model_info.tokenizer,
            tokenizer_mode=model_info.tokenizer_mode,
            speculative_config={
                "model": model_info.speculative_model,
                "num_speculative_tokens": 1,
            } if model_info.speculative_model else None,
            trust_remote_code=model_info.trust_remote_code,
            load_format="dummy",
            hf_overrides=hf_overrides,
        )
