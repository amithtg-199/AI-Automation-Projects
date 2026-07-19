import mistralai
print("Version:", getattr(mistralai, "__version__", "unknown"))
print("Dir mistralai:", dir(mistralai))

try:
    import mistralai.client
    print("Dir mistralai.client:", dir(mistralai.client))
except Exception as e:
    print("client err", e)

try:
    from mistralai.client import MistralClient
    print("MistralClient exists")
except Exception as e:
    print("MistralClient error:", e)

try:
    from mistralai import Mistral
    print("Mistral exists")
except Exception as e:
    print("Mistral error:", e)
