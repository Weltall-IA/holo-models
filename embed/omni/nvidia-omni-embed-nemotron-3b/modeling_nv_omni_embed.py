import torch
from transformers import Qwen2_5OmniThinkerTextModel, Qwen2_5OmniThinkerForConditionalGeneration
from transformers.cache_utils import Cache
from transformers.modeling_attn_mask_utils import _prepare_4d_attention_mask
from transformers.models.qwen2_5_omni.configuration_qwen2_5_omni import Qwen2_5OmniThinkerConfig

class BidirectQwen2_5OmniThinkerTextModel(Qwen2_5OmniThinkerTextModel):

    def __init__(self, config):
        super().__init__(config)
        for layer in self.layers:
            layer.self_attn.is_causal = False

    # override the _update_causal_mask method to generate bi-directional attention
    def _update_causal_mask(
        self,
        attention_mask: torch.Tensor,
        input_tensor: torch.Tensor,
        cache_position: torch.Tensor,
        past_key_values: Cache,
        output_attentions: bool = False,
    ):
        calculated_attention_mask = super()._update_causal_mask(
        attention_mask,
        input_tensor,
        cache_position,
        past_key_values,
        output_attentions)
        if calculated_attention_mask is None:
            return None
        if self.config._attn_implementation == "flash_attention_2":
            if attention_mask is not None and 0.0 in attention_mask:
                return attention_mask
        causal_mask = _prepare_4d_attention_mask(
            attention_mask,
            dtype=input_tensor.dtype,
        )
        return causal_mask

class NVOmniEmbedConfig(Qwen2_5OmniThinkerConfig):
    model_type = "nvomniembed"

class NVOmniEmbedModel(Qwen2_5OmniThinkerForConditionalGeneration):
    config_class = NVOmniEmbedConfig
    def __init__(self, config):
        super().__init__(config)
        self.model = BidirectQwen2_5OmniThinkerTextModel._from_config(
            config.text_config, attn_implementation=config._attn_implementation
        )
    