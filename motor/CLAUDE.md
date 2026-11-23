# motor/ — padrões de código
- Código único para todos os canais. Nada específico de canal dentro do motor: o que é do canal fica em canais/<canal>/.
- Todo comando recebe --canal e --formato (ex.: `m5 previa --canal principal --formato longo`).
- Todo gerador é módulo reutilizável (F11) + entrada em geradores.yaml + amostra aprovada por Pedro (F09). Gerador novo depois da construção: F10.
- O motor é determinístico, sem IA. Nunca chuta: sem correspondência → exceção (F07).
- Versões travadas: requirements.txt, package-lock.json, versoes_sistema.txt. Atualizar só por ordem de Pedro (F23).
- geradores.yaml, requirements.txt, package-lock.json, versoes_sistema.txt: escrita só com ordem explícita de Pedro, mostrando o diff, commit identificado (6.3).
