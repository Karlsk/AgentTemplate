import time
import asyncio
from app.core.llm.embedding import EmbeddingFactory, EmbeddingConfig
from app.core.common.logging import TerraLogUtil as logger

async def benchmark_embedding():
    # Mock config for BGE-large or similar open-source model
    # Note: In real test, this should point to an actual local model or OpenAI
    config = EmbeddingConfig(
        model_name="BAAI/bge-large-zh-v1.5",
        dimensions=1024,
        batch_size=32,
        device="cpu" # Use "cuda" if GPU is available
    )
    
    embedding_model = EmbeddingFactory.get_embedding(config)
    
    # 32 texts with 512 tokens each (roughly 1000 characters)
    texts = ["测试文本 " * 250 for _ in range(32)]
    
    print(f"Starting benchmark with {len(texts)} texts...")
    
    t0 = time.perf_counter()
    embeddings = embedding_model.embed(texts)
    elapsed = (time.perf_counter() - t0) * 1000 # ms
    
    print(f"Benchmark finished.")
    print(f"Total time: {elapsed:.2f} ms")
    print(f"Average per batch: {elapsed:.2f} ms")
    print(f"Embedding dimension: {len(embeddings[0])}")
    
    if elapsed < 600:
        print("PERFORMANCE REQUIREMENT MET (< 600 ms)")
    else:
        print("PERFORMANCE REQUIREMENT NOT MET (> 600 ms)")

if __name__ == "__main__":
    asyncio.run(benchmark_embedding())
