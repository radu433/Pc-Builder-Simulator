export const articoleFullContent = {
  "1": {
    titlu: "Cum alegi sursa (PSU) corectă?",
    autor: "Echipa PC Builder",
    data: "15 Mai 2024",
    continut: `
      <h2>1. Puterea contează</h2>
      <p>Nu cumpăra o sursă de 1000W dacă sistemul tău consumă 300W. O marjă de 20-30% peste consumul maxim (TDP) al CPU + GPU este ideală.</p>
      <h3>2. Certificarea 80 PLUS</h3>
      <p>Caută cel puțin 80+ Bronze, dar recomandarea noastră pentru gaming este <b>80+ Gold</b>.</p>
    `
  },
  "2": {
    titlu: "Diferența dintre RAM DDR4 și DDR5",
    autor: "Expert Hardware",
    data: "10 Mai 2024",
    continut: `
      <h2>Generația contează</h2>
      <p>DDR5 oferă lățime de bandă dublă, dar verifică dacă placa ta de bază o suportă. Sloturile NU sunt compatibile între ele!</p>
    `
  },
  "4": {
    titlu: "Cele mai bune carcase sub 400 RON",
    autor: "Reviewer PC",
    data: "05 Mai 2024",
    continut: `
      <h2>Focus pe Airflow</h2>
      <p>La acest buget, caută carcase care vin cu cel puțin 3 ventilatoare incluse și panou frontal de tip 'Mesh' (sită).</p>
    `
  },
  "asamblare": {
    titlu: "Ghidul Suprem de Asamblare PC (2026)",
    autor: "Echipa PC Builder",
    data: "Actualizat recent",
    continut: `
      <h2>Pasul 1: Pregătirea și uneltele necesare</h2>
      <p>Înainte de a începe, asigură-te că ai un spațiu de lucru curat, bine iluminat și lipsit de covoare (pentru a evita electricitatea statică). Ai nevoie doar de o <strong>șurubelniță în cruce (Phillips #2)</strong> și de o masă liberă.</p>

      <h2>Pasul 2: Instalarea Procesorului (CPU)</h2>
      <p>Acesta este cel mai delicat pas. Scoate placa de bază din cutie și așeaz-o pe cutia ei de carton (este o suprafață sigură).</p>
      <ul>
        <li>Ridică brațul metalic al socket-ului de pe placa de bază.</li>
        <li>Aliniază triunghiul auriu din colțul procesorului cu triunghiul marcat pe socket.</li>
        <li>Lasă procesorul să cadă ușor la locul lui (<strong>NU</strong> apăsa pe el!).</li>
        <li>Coboară brațul metalic și fixează-l sub clemă. Capacul de plastic va sări singur.</li>
      </ul>

      <h2>Pasul 3: Memoria RAM și Stocarea (M.2 NVMe)</h2>
      <p>E mult mai ușor să instalezi aceste piese acum, în afara carcasei. Pentru memoria RAM (dacă ai 2 plăcuțe), folosește de obicei sloturile <strong>2 și 4</strong> pentru a activa modul Dual-Channel și a obține performanță maximă.</p>

      <h2>Pasul 4: Montarea în carcasă</h2>
      <p>Așează cu grijă placa de bază în carcasă peste distanțierele metalice (standoffs). Asigură-te că porturile din spate se aliniază cu decupajul (I/O Shield-ul) și înșurubează placa pe poziție.</p>

      <h2>Pasul 5: Conectarea Sursei (PSU)</h2>
      <p>Instalează sursa în locașul ei. Cele mai importante cabluri pe care trebuie să le tragi acum sunt:</p>
      <ul>
        <li><strong>Cablul de 24-pini:</strong> Cel mai gros cablu, merge în marginea dreaptă a plăcii de bază.</li>
        <li><strong>Cablul CPU de 8-pini:</strong> Merge de obicei în colțul din stânga-sus.</li>
      </ul>

      <h2>Pasul 6: Placa Video (GPU)</h2>
      <p>Scoate tăblițele de protecție din spatele carcasei, deschide clema slotului lung (PCIe x16) de pe placa de bază și apasă placa video până auzi un "click". Securizeaz-o cu 1-2 șuruburi de carcasă și bagă-i cablurile de alimentare (PCIe).</p>

      <h2>Pasul 7: Primul Boot!</h2>
      <p>Ai terminat greul! Acum conectează monitorul <strong>direct în placa video</strong> (nu în placa de bază!), dă drumul la sursă de la butonul I/O din spate și apasă butonul Power al carcasei. Dacă vezi pe ecran mesajul de a intra în BIOS, felicitări, ai asamblat cu succes un PC!</p>
    `
  }
};