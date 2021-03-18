"""
auto_clm.py

Default Causal Language Model (CLM) & Tokenizer Specification and Initialization. Downloads Model Configuration (if
necessary) from the  Hugging Face `transformers` Hub, instantiates pretrained Tokenizer, and initializes model using
the necessary AutoModel class.
"""
import logging
import math
from pathlib import Path
from typing import Dict, Tuple

from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer, PreTrainedTokenizer

from ..util import REGISTRY


# Nest Overwatch under root `mistral` logger, inheriting formatting!
overwatch = logging.getLogger("mistral.models.auto")


def gpt_initialize(model: AutoModelForCausalLM, initializer_range: float = 0.02, n_layer: int = 12) -> None:
    """
    Re-initialize model weights subject to the OpenAI GPT initialization described in the paper:

    > A modified initialization which accounts for the accumulation on the residual path with model depth. We scale
    > the weights of residual layers at initialization by a factor of 1/√N where N is the number of residual layers.
    >   -- GPT-2 :: https://openai.com/blog/better-language-models/

    Reference --> Megatron-LM :: https://github.com/NVIDIA/Megatron-LM/blob/main/megatron/model/gpt_model.py

    :param model: GPT-X Model (via AutoModel) to re-initialize subject to the above scheme.
    :param initializer_range: Standard Deviation for Truncated Normal Initializer (from GPT-2 Config)
    :param n_layer: Number of Transformer Layers --> LayerNorm/Residual Blocks = 2 * n_layer (1 for Attn, 1 for MLP)

    :return: Re-initialized GPT-X model with weights initialized as above.
    """
    # As per Megatron-LM --> All we really want to do is re-initialize all the residual (c_proj) weights!
    for name, p in model.named_parameters():
        if "c_proj" in name and "weight" in name:
            # Special Scaled Initialization --> There are 2 Layer Norms per Transformer Layer [Block]
            p.data.normal_(mean=0.0, std=initializer_range / math.sqrt(2.0 * n_layer))


def get_auto_clm_tokenizer(
    model_id: str, paths: Dict[str, Path], use_pretrained_tokenizer: bool = True
) -> Tuple[AutoModelForCausalLM, PreTrainedTokenizer]:
    """ Download/Load AutoConfig and Instantiate Corresponding Model and Tokenizer. """

    # Create Configuration
    overwatch.info(f"Fetching Hugging Face AutoConfig for Model: `{REGISTRY[model_id]}`...")
    config = AutoConfig.from_pretrained(REGISTRY[model_id], cache_dir=paths["configs"])

    # Create Tokenizer
    overwatch.info(f"Fetching Hugging Face [Fast] AutoTokenizer for Model: `{REGISTRY[model_id]}`...")
    if use_pretrained_tokenizer:
        tokenizer = AutoTokenizer.from_pretrained(REGISTRY[model_id], config=config, cache_dir=paths["tokenizer"])
    else:
        overwatch.error("Tokenizer Training/Initialization (from Scratch) not yet implemented!")
        raise NotImplementedError()

    # Initialize Model
    overwatch.info(f"Initializing Tabula Rasa Model from Configuration: `{REGISTRY[model_id]}`...")
    model = AutoModelForCausalLM.from_config(config)
    model.resize_token_embeddings(len(tokenizer))

    # Get New GPT-2 Specific Initializer
    gpt_initialize(model, initializer_range=config.initializer_range, n_layer=config.n_layer)

    return model, tokenizer
