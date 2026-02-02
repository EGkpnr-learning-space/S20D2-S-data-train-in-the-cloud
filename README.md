# 🪐 Bulut Bilişim Dünyasına Giriş! 🚀

Bir önceki ünitede, WorkinTech Veri Bilimi ekibinin not defterini **paketlediniz** 📦 ve "küçük" bir yerel makinede çalıştırmasına rağmen modelin tam _TaxiFare_ veri seti üzerinde eğitilebilmesi için kodu **parça-işleme** ile güncellediniz.

☁️ Bu ünitede, yerel makinenizi kullanmak yerine işi **bulut kaynaklarına** nasıl dağıtacağınızı öğreneceksiniz.

💪 Artık (teorik olarak) seçtiğiniz RAM boyutunda bir makineye erişebildiğiniz için, artık "parça-parça" mantığına ihtiyacınız olmadığını varsayacağız!

🎯 Bugün, önceki ünitenin kod tabanını yeniden düzenleyecek ve şunları yapacaksınız:
- `params.py`'yi güncellemek yerine tüm ortam değişkenlerinizi tek bir `.env` dosyasından alın
- Ham veriyi WorkinTech BigQuery'den belleğe tek seferde yükleyin (parça yok)
- Veriyi iki kez sorgulamaktan kaçınmak için yerel bir CSV kopyası önbelleğe alın
- Veriyi işleyin
- İşlenmiş veriyi kendi BigQuery tablonuza yükleyin
- İşlenmiş veriyi indirin (tek seferde)
- Veriyi iki kez sorgulamaktan kaçınmak için yerel bir CSV kopyası önbelleğe alın
- Modelinizi bu işlenmiş veri üzerinde eğitin
- Model ağırlıklarını kendi Google Cloud Storage (GCS) kovasında saklayın

Ardından, tüm bu iş akışını VM üzerinde çalıştırmak için bir Sanal Makine (VM) sağlayacaksınız!

Tebrikler, **Veri Bilimci**'den tam **ML Mühendisi**'ne dönüştünüz!
Artık büyük GPU dizüstü bilgisayarınızı satıp gerçek ML uygulayıcıları gibi hafif bir bilgisayar alabilirsiniz 😝

---

<br>

# 1️⃣ Yeni taxifare paketi kurulumu

<details>
  <summary markdown='span'><strong>❓Talimatlar (genişletmek için tıklayın)</strong></summary>


## Proje Yapısı

👉 Bundan sonra, her yeni meydan okumaya önceki meydan okumanın çözümüyle başlayacaksınız.

👉 Her yeni meydan okuma ek özellik seti getirecek.

İlgilenilen ana dosyalar şunlardır:
```bash
.
├── .env                            # ⚙️ Single source of all config variables
├── .envrc                          # 🎬 .env automatic loader (used by direnv)
├── Makefile                        # New commands "run_train", "run_process", etc..
├── README.md
├── requirements.txt
├── setup.py
├── taxifare
│   ├── __init__.py
│   ├── interface
│   │   └── main_local.py           # 🚪 (OLD) entry point
│   │   └── main.py                 # 🚪 (NEW) entry point: No more chunks 😇 - Just process(), train()
│   ├── ml_logic
│       ├── data.py                 # (UPDATED) Loading and storing data from/to BigQuery !
│       ├── registry.py             # (UPDATED) Loading and storing model weights from/to Cloud Storage!
│       ├── ...
│   ├── params.py                   # Simply load all .env variables into python objects
│   └── utils.py
└── tests
```


#### ⚙️ `.env.sample`

Bu dosya, her meydan okuma için bir `.env` dosyası oluşturmanıza yardımcı olmak için tasarlanmış bir _şablondur_. `.env.sample` dosyası, kod tarafından gerekli olan ve `.env` dosyasında beklenen değişkenleri içerir. 🚨 `.env` dosyasının içeriğini açığa çıkarmamak için **asla Git ile takip edilmemesi** gerektiğini unutmayın, bu nedenle onu `.gitignore`'a ekledik.

#### 🚪 `main.py`

Hoşçakal `taxifare.interface.main_local` modülü, bize iyi hizmet ettin ❤️

Yaşasın `taxifare.interface.main`, yeni paket giriş noktası ⭐️:

- `preprocess`: veriyi önişle ve `data_processed` sakla
- `train`: işlenmiş veri üzerinde eğit ve model ağırlıklarını sakla
- `evaluate`: en son eğitilmiş modelin yeni veriler üzerindeki performansını değerlendir
- `pred`: eğitilmiş modelin belirli bir sürümüyle bir `DataFrame` üzerinde tahmin yap


🚨 Pakette kodun ana değişikliği, `main.py` dosyasının boyutunu sınırlamak için işinin bir kısmını özel modüllere devretmeyi seçmemizdir. Ana değişiklikler şunları içerir:

- Proje yapılandırması: tek gerçeklik kaynağı `.env`'dir
  - `.envrc`, `direnv`'e `.env`'i ortam değişkenleri olarak yüklemesini söyler
  - `params.py` daha sonra tüm bu değişkenleri python'a yükler ve artık manuel olarak değiştirilmemelidir

- `registry.py`: kod, eğitilmiş modeli yerel olarak veya - _spoiler uyarısı_ - bulutta saklamak için gelişti
  - Yeni ortam değişkeni `MODEL_TARGET`'a dikkat edin (`local` veya `gcs`)

- `data.py`, `main.py`'de yoğun olarak kullanacağımız 2 metodu yeniden düzenledik
  - `get_data_with_cache()` (BigQuery'den veya varsa önbelleğe alınmış CSV'den veri al)
  - `load_data_to_bq()` (bazı verileri BQ'ya yükle)



## Kurulum

#### `taxifare` sürüm `0.0.7`'yi yükleyin

**💻 Yeni paket sürümünü yükleyin**
```bash
make reinstall_package # always check what make does in the Makefile
```

**🧪 Paket sürümünü kontrol edin**
```bash
pip list | grep taxifare
# taxifare               0.0.7
```

#### direnv & .env kurulumu

Amacımız, _paketimizin_ 📦 davranışını bir `.env` proje yapılandırma dosyasında tanımlanan değişkenlerin değerlerine bağlı olarak yapılandırabilmektir.

**💻 Bunu yapabilmek için, `direnv` shell uzantısını yükleyeceğiz.** Görevi, projenin üst dizin yapısında en yakın `.env` dosyasını bulmak ve içeriğini ortama yüklemektir.

``` bash
# MacOS
brew install direnv

# Ubuntu (Linux or Windows WSL2)
sudo apt update
sudo apt install -y direnv
```
`direnv` yüklendikten sonra, shell her başladığında `direnv`'i yüklemesi için `zsh`'a söylememiz gerekiyor

``` bash
code ~/.zshrc
```

`.zshrc` dosyanızdaki eklentiler listenizin sonuna `direnv`'i ekleyin
Bittiğinizde, şunun gibi görünmelidir:

``` bash
plugins=(git gitfast ... direnv)
```

`direnv`'i yüklemek için yeni bir `zsh` penceresi başlatın

**💻 Bu noktada, `direnv` hala hiçbir şey yükleyemiyor, çünkü `.env` dosyası yok, o halde bir tane oluşturalim:**

- `env.sample` dosyasını kopyalayın ve kopyasını `.env` olarak yeniden adlandırın
- `direnv allow .` ile proje yapılandırmasını etkinleştirin (`.` _geçerli dizin_ anlamına gelir)

🧪 `direnv`'in `.env` dosyasından ortam değişkenlerini okuyabildiğini kontrol edin:

```bash
echo $DATA_SIZE
# 1k --> Let's keep it small!
```

Bundan sonra, projenin davranışını güncellemeniz gereken her seferinde:
1. `.env`'yi düzenleyin, kaydedin
2. Sonra
```bash
direnv reload . # to reload your env variables 🚨🚨
```

**☝️ Bunu *unutacaksınız*. Yanıldığımızı kanıtlayın 😝**

```bash
# Tamam, bu ünit için, her zaman veri boyutu değerlerini küçük tutun (geliştirme amaçları için iyi uygulama)
DATA_SIZE=1k
CHUNK_SIZE=200
```

</details>

# 2️⃣ GCP Kurulumu

<details>
<summary markdown='span'><strong>❓Talimatlar (genişletmek için tıklayın)</strong></summary>

**Google Cloud Platform** buluttaki uzak kaynaklara erişmenizi ve bunları kullanmanızı sağlayacaktır. Bununla şunlar aracılığıyla etkileşim kurabilirsiniz:
- 🌐 [console.cloud.google.com](https://console.cloud.google.com)
- 💻 Komut Satırı Araçları
  - `gcloud`
  - `bq` (BigQuery - SQL)
  - `gsutils` (bulut depolama - kovalar)


### a) `gcloud` CLI

- Kendi **GCP proje ID**'nizi listeleyen `gcloud` komutunu bulun.
- 📝 GCP projenizin ID'siyle `.env` proje yapılandırmasındaki `GCP_PROJECT` değişkenini doldurun
- 🧪 Testleri `make test_gcp_project` ile çalıştırın

<details>
  <summary markdown='span'><strong>💡 İpucu </strong></summary>


  `gcloud` komutları veya alt komutları hakkında bağlamsal yardım almak için `-h` veya `--help` (daha fazla ayrıntı) bayraklarını kullanabilirsiniz; `gcloud billing` alt komutunun yardımını almak için `gcloud billing -h` kullanın veya daha ayrıntılı yardım için `gcloud billing --help` kullanın.

  👉 Eğer komut kendiliğinden sonlanmadıysa (`Ctrl + C` de çalışır) yardım modundan çıkmak genellikle `q` tuşuna basmaktır

  Ayrıca `gcloud`'u argümansiz çalıştırmanın tüm mevcut alt komutları gruplara göre listelediğini unutmayın.

</details>

### b) Cloud Storage (GCS) ve `gsutil` CLI

Sık sık kullanacağınız ikinci CLI aracı, Cloud Storage üzerinde **kovalar** içinde saklanan dosyalarla uğraşmanızı sağlar.

Bunu model ağırlıkları gibi büyük ve yapılandırılmamış verileri saklamak için kullanacağız :)

**💻 `gsutil` kullanarak GCP hesabınızda bir kova oluşturun**

- Kovası kendinizin bulunduğu yerde oluşturduğunuzdan emin olun (`.env`'deki `GCP_REGION`'i kullanın)
- Ayrıca `BUCKET_NAME` değişkenini seçtiğiniz isimle doldurun (global olarak benzersiz ve küçük harf olmalı! GitHub kullanıcı adınızda büyük harf varsa, küçük harfe çevirmeniz gerekecek!)

örn.
```bash
BUCKET_NAME = taxifare_<user.github_nickname>
```
- `direnv reload .` ;)

İpucu: CLI, `.env` değişkenlerini `$` işareti ile ön ek yaparak enterpolasyon yapabilir (örn. `$GCP_REGION`)
<details>
  <summary markdown='span'>🎁 Çözüm</summary>

```bash
# kovaları listele
gsutil ls

# kova oluştur
gsutil mb \
    -l $GCP_REGION \
    -p $GCP_PROJECT \
    gs://$BUCKET_NAME

# kovası sil
gsutil rm -r gs://$BUCKET_NAME
```
Kova oluşturmak veya mevcut kovaları ve içeriklerini listelemek için [Cloud Storage konsolunu](https://console.cloud.google.com/storage/) da kullanabilirsiniz.

GCP konsolunun (web arabirimi) komut satırına kıyasla ne kadar yavaş olduğunu görüyor musunuz?

</details>

**🧪 Testleri `make test_gcp_bucket` ile çalıştırın**

### c) BigQuery ve `bq` CLI

BigQuery, hızla sorgulanabilen yapılandırılmış verileri saklamak için kullanılan bir veri ambarıdır.

💡 Daha kesin olmak gerekirse, BigQuery çevrimiçi büyük ölçekli paralel bir **Analitik Veritabanı**'dır (**İşlemsel Veritabanı**'nın aksine)

- Veriler sütunlara göre saklanır (örneğin PostgreSQL'de satırların aksine)
- `group-by`, `join`, `where` vb. gibi büyük dönüşümler için optimize edilmiştir.
- Ancak sık satır-satır ekleme/silme için optimize edilmemiştir

WorkinTech aslında Django uygulamasının günde yüz binlerce bireysel işlemi saklamak/okumak için kullandığı ana üretim veritabanı olarak yönetilen bir PostgreSQL (örn. [Google Cloud SQL](https://cloud.google.com/sql)) kullanıyor!

Her gece, WorkinTech "ana" PostgresSQL'in günlük farklarını "kopya" BigQuery ambarına uygulayan bir "veritabanı replikasyonu" işi başlatıyor. Neden?
- Çünkü üretim-veritabanınıza karşı doğrudan sorgu çalıştırmak istemezsiniz! Bu kullanıcılarınızı yavaşlatabilir.
- Çünkü sütunlu veritabanlarında analiz daha hızlı/ucuzdur.
- Çünkü ayrıca ambarınıza diğer verileri entegre ederek JOIN yapmak istersiniz (örn. Google Ads'den pazarlama verileri, ...).

👉 İşimize geri dönelim:

**💻 İşlenmiş verileri saklayacağımız ve sorgulayacağımız kendi veri setimizi oluşturalim !**

- `bq` ve aşağıdaki ortam değişkenlerini kullanarak, kendi `GCP_PROJECT`'inizde `taxifare` adında yeni bir _veri seti_ oluşturun

```bash
BQ_DATASET=taxifare
BQ_REGION=...
GCP_PROJECT=...
```

- Ardından 3 yeni _tablo_ ekleyin `processed_1k`, `processed_200k`, `processed_all`

<details>
  <summary markdown='span'>💡 İpuçları</summary>

`bq` komutu makinenizde yüklediğiniz **Google Cloud SDK**'nın bir parçası olmasına rağmen, `gcloud` ve `gsutil` komutlarıyla aynı yardım desen ini takip etmiyor gibi görünüyor.

Mevcut alt komutları listelemek için `bq`'yu argümansiz çalıştırmayı deneyin.

Aradığınız şey muhtemelen `mk` (make) bölümündedir.
</details>

<details>
  <summary markdown='span'><strong>🎁 Çözüm </strong></summary>

``` bash
bq mk \
    --project_id $GCP_PROJECT \
    --data_location $BQ_REGION \
    $BQ_DATASET

bq mk --location=$GCP_REGION $BQ_DATASET.processed_1k
bq mk --location=$GCP_REGION $BQ_DATASET.processed_200k
bq mk --location=$GCP_REGION $BQ_DATASET.processed_all

bq show
bq show $BQ_DATASET
bq show $BQ_DATASET.processed_1k

```

</details>

**🧪 Testleri `make test_big_query` ile çalıştırın**


🎁 `make reset_all_files` direktifine bakın --> Tüm yerel dosyaları (csv'ler, modeller, ...) ve bq tabloları ile kovalardan verileri sıfırlar, ancak yerel klasör yapısını, bq tablo şemasını ve gsutil kovalarını korur.

Emin değilseniz meydan okumanin durumunu sıfırlamak ve kendinizi hata ayıklamak için çok yararlı!

👉 Şimdi `make reset_all_files`'i güvenle çalıştırın, ünit 01'den dosyaları kaldıracak ve daha net hale getirecek

👉 Boş bir durumdan geri döndüğünüzü görmek için `make show_sources_all` çalıştırın!

✅ Her şey hazır olduğunda, sonuçlarınızı Kitt'te `make test_kitt` ile takip edin (beklemeyin, bu 1dk'dan fazla sürüyor)

</details>

# 3️⃣ ⚙️ Yerel olarak eğitin, verilerle bulutta !

<details>
  <summary markdown='span'><strong>❓Talimatlar (genişletmek için tıklayın)</strong></summary>

🎯 Amacınız, 4 rotayı _teker teker_ çalıştırabilmeniz için `taxifare.interface.main`'i doldurmaktır

```python
if __name__ == '__main__':
    # preprocess()
    # train()
    # evaluate()
    # pred()
```

Bunu yapmak için şunlardan birini yapabilirsiniz:

- 🥵 Yukarıdaki rotaları teker teker yorumdan çıkarın ve Terminal'inizden `python -m taxifare.interface.main` çalıştırın

- 😇 Daha akıllıca: Aşağıda sizin için oluşturduğumuz `make` komutlarının her birini kullanın

💡 Her fonksiyon docstring'ini dikkatle okuduğunuzdan emin olun
💡 Rota tamamlamayı paralelleştirmeye çalışmayın. Bunları teker teker düzeltin.
💡 Ayrıca `data.py`'de `load_data_to_bq()` fonksiyonunu kodlamanız gerekecek.
💡 Traceback'leri dikkatle okumak için zaman ayırın ve kodunuza veya testin kendisine breakpoint() ekleyin (artık mühendissiniz)!

**Önişleme (Preprocess)**

💡 Gerektiğinde `main_local.py`'ye geri dönmekten çekinmeyin! Bazı sözdizimi yeniden kullanılabilir

```bash
# preprocess() fonksiyonunu çağırın
make run_preprocess
# Ardından bu rotayı test edin, ancak tüm durum kombinasyonlarıyla (.env, cached_csv var mı yok mu)
make test_preprocess
```

**Eğitim (Train)**

💡 MODEL_TARGET = 'gcs' vs 'local' olduğunda ne olduğunu anlamaktan emin olun
💡 Loglarınızı kısaltmak için model eğitiminde `verbose=0` ayarlamanızı tavsiye ediyoruz!

```bash
make run_train
make test_train
```

**Değerlendirme (Evaluate)**

MODEL_TARGET = 'gcs' vs 'local' olduğunda ne olduğunu anlamaktan emin olun
```bash
make run_evaluate
make test_evaluate
```

**Tahmin (Pred)**

Bu kolay
```bash
make run_pred
make test_pred
```

✅ Her şey hazır olduğunda, sonuçlarınızı Kitt'te `make test_kitt` ile takip edin

🏁 Ağır yeniden düzenleme için tebrikler! Artık `DATA_SIZE='all'` ile kullanılmak üzere bulutta deploy edilebilecek çok sağlam bir paketiniz var 💪

</details>

# 4️⃣ Sanal Makinelerle Bulutta Eğitim


<details>
  <summary markdown='span'><strong>❓Talimatlar (genişletmek için tıklayın)</strong></summary>


## Compute Engine Servisini Etkinleştirin

GCP'de, birçok servis varsayılan olarak etkin değildir. _sanal makineler_ kullanmak için etkinleştirilecek servis **Compute Engine**'dir.

**❓Bir GCP servisini nasıl etkinleştirirsiniz?**

Bir **servis**'i etkinleştirmek için `gcloud` komutunu bulun.

<details>
  <summary markdown='span'>💡 İpuçları</summary>

[Bir API'yi Etkinleştirme](https://cloud.google.com/endpoints/docs/openapi/enable-api#gcloud)
</details>

## İlk Sanal Makinenizi Oluşturun

`taxifare` paketi buluttaki bir makinede eğitim almaya hazır. İlk *Sanal Makine* instance'ımızı oluşturalim!

**❓Sanal Makine Oluşturun**

GCP konsoluna, özellikle [Compute Engine sayfasına](https://console.cloud.google.com/compute) gidin. Konsol mevcut seçenekleri kolayca keşfetmenizi sağlayacaktır. Bir **Ubuntu** instance' ı oluşturduğunuzdan emin olun (aşağıdaki _nasıl-yapılır_'ı okuyun ve ardından _ipucu_na bakın).

<details>
  <summary markdown='span'><strong> 🗺 VM instance'inızı nasıl yapılandıracağınız </strong></summary>


  Mevcut seçenekleri keşfedin. Arabirimin sağ üstü, VM sürekli çevrimiçi kalırsa seçilen parametreler için aylık maliyet tahmini verir.

  Varsayılan seçeneklerin çoğu şimdi yapmak istediğimiz için yeterli olmalı, bunlar hariç:

  - Instance'in **"Adını"** anlamlı bir şeyle değiştirin, `taxi-instance` uygun olacaktır.

  - **"Bölge"'yi** daha önce Cloud Storage için kullandığınızla değiştirin: VM'miz ile kova'nın aynı bölgede olmasını istiyoruz, bölgeler arası (daha yavaş) veri transferini önlemek için.

  - VM instance'inin işletim sistemini değiştirin:

    Sol sütunda, **"OS ve depolama"** bölümüne gidin ve **"DEĞİŞTİR"**'e tıklayın. **"İşletim sistemi"**'ni **"Ubuntu"** olarak değiştirin ve **"Sürüm"**'u en son **"Ubuntu xx.xx LTS x86/64"** (Uzun Süreli Destek) sürümü olarak değiştirin. ("Minimal" sürüm seç<u>meyin</u>: çok fazla aracı manuel olarak yüklememiz gerekir.)

    Ubuntu, makinenizdeki yapılandırmaya en çok benzeyecek [Linux dağıtımıdır](https://en.wikipedia.org/wiki/Linux_distribution). Mac'te, Windows WSL2 kullanıyor veya yerel Linux'te olmanızdan bağımsız, bu seçeneği seçmek zaten aşina olduğunuz komutları kullanarak uzak bir makineyle oynamanızı sağlayacaktır.

</details>

<details>
  <summary markdown='span'><strong>💡 İpucu </strong></summary>

  Gelecekte, tam olarak ne tür bir VM oluşturmak istediğinizi bildiğinizde, her şeyi komut satırından yapmak istiyorsanız `gcloud compute instances` komutunu kullanabileceksiniz; örneğin:

  ``` bash
  INSTANCE=taxi-instance
  IMAGE_PROJECT=ubuntu-os-cloud
  IMAGE_FAMILY=ubuntu-2404-lts-amd64
  ZONE=europe-west1-b

  gcloud compute instances create $INSTANCE --image-project=$IMAGE_PROJECT --image-family=$IMAGE_FAMILY --zone=$ZONE
  ```
</details>

**💻 `.env` proje yapılandırmasındaki `INSTANCE` değişkenini doldurun**


## VM'nizi Kurun

Parmaklarınızın ucunda, eğitimler veya aklınıza gelebilecek diğer her tür görevde yardım etmeye hazır, neredeyse sınırsız bilgi işlem gücüne erişiminiz var.

**❓VM'ye nasıl bağlanırsınız?**

GCP konsolu, bir web arabirimi üzerinden VM instance'ina bağlanmanıza olanak tanır:

<a href="/gce-vm-ssh.png"><img src="/gce-vm-ssh.png" height="450" alt="gce vm ssh"></a><a href="/GCE_SSH_in_browser.png"><img style="margin-left: 15px;" src="/GCE_SSH_in_browser.png" height="450" alt="gce console ssh"></a>

`exit` yazarak veya pencereyi kapatarak bağlantıyı kesebilirsiniz.

Güzel bir alternatif, sanal makineye doğrudan komut satırınızdan bağlanmaktır 🤩

<a href="/GCE_SSH_in_terminal.png"><img src="/GCE_SSH_in_terminal.png" height="450" alt="gce ssh"></a>

Tek yapmanız gereken çalışan bir instance üzerinde `gcloud compute ssh` yapmak ve bağlantıyı kesmek istediğinizde `exit` çalıştırmak 🎉

``` bash
INSTANCE=taxi-instance

gcloud compute ssh $INSTANCE
```

<details>
  <summary markdown='span'><strong>💡 Hata 22 </strong></summary>


  Eğer `port 22: Connection refused` hatası alırsanız, VM instance'in başlangıcını tamamlaması için biraz daha bekleyin.

  Hangi makinede komutlarınızı çalıştırdığınızı merak ediyorsanız sadece `pwd` veya `hostname` çalıştırın.
</details>

**❓Python kodunuzu çalıştırmak için VM'yi nasıl kurarsınız?**
<a href="https://github.com/Workintech/data-science-kurulum/tree/master">https://github.com/Workintech/data-science-kurulum/tree/master</a>

**💻 VM instance'inıza bağlanın ve aşağıdaki bölümlerin komutlarını çalıştırın**

<details>
  <summary markdown='span'><strong> ⚙️ <code>zsh</code> ve <code>omz</code> (genişletmek için tıklayın)</strong></summary>

**zsh** shell'i ve **Oh My Zsh** çerçevesi zaten aşina olduğunuz _CLI_ yapılandırmasıdır. Sorulduğunda, `zsh`'i varsayılan shell yapma kabül ettiğinizden emin olun.

``` bash
sudo apt update
sudo apt install -y zsh
sh -c "$(curl -fsSL https://raw.github.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
```

👉 Şimdi uzak makinenin _CLI_'si yerel makinenizin _CLI_'sine biraz daha benzemeye başlıyor
</details>

<details>
  <summary markdown='span'><strong> ⚙️ <code>pyenv</code> ve <code>pyenv-virtualenv</code> (genişletmek için tıklayın)</strong></summary>

`pyenv` ve `pyenv-virtualenv` depolarını VM üzerinde klonlayın:

``` bash
git clone https://github.com/pyenv/pyenv.git ~/.pyenv
git clone https://github.com/pyenv/pyenv-virtualenv.git ~/.pyenv/plugins/pyenv-virtualenv
```

~/.zshrc'yi Terminal kod editöründe açın:

``` bash
nano ~/.zshrc
```

`~/.zshrc`'deki `plugins=(git)` satırındaki `zsh` eklentileri listesine `pyenv`, `ssh-agent` ve `direnv` ekleyin: sonunda, `plugins=(git pyenv ssh-agent direnv)` olmalısınız. Ardından, çıkın ve kaydedin (`Ctrl + X`, `Y`, `Enter`).

Değişikliklerin gerçekten kaydedildiğinden emin olun:

``` bash
cat ~/.zshrc | grep "plugins="
```

pyenv başlatma scriptini `~/.zprofile`'nize ekleyin:

``` bash
cat << EOF >> ~/.zprofile
export PYENV_ROOT="\$HOME/.pyenv"
export PATH="\$PYENV_ROOT/bin:\$PATH"
eval "\$(pyenv init --path)"
EOF
```

👉 Şimdi Python kurmaya hazırız

</details>

<details>
  <summary markdown='span'><strong> ⚙️ <code>Python</code> (genişletmek için tıklayın)</strong></summary>

Python derlemek için gerekli bağımlılıkları ekleyin:

``` bash
sudo apt-get update; sudo apt-get install make build-essential libssl-dev zlib1g-dev \
libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev \
python3-dev
```

ℹ️ Eğer hangi servisleri yeniden başlatacağınızı soran bir pencere çıkarsa, sadece *Enter*'a basın:

<a href="/gce-apt-services-restart.png"><img src="/gce-apt-services-restart.png" width="450" alt="gce apt services restart"></a>

Şimdi `~/.zshrc` ve `~/.zprofile`'deki güncellemelerin dikkate alınması için yeni bir kullanıcı oturumu başlatmamız gerekiyor. Aşağıdaki komutu çalıştırın 👇:

``` bash
zsh --login
```

WorkinTech'in kullandığı aynı python sürümünü yükleyin ve bir `taxifare-env` sanal ortam oluşturun. Bu biraz zaman alabilir ve takılı gibi görünebilir, ama değildir:

``` bash
pyenv install 3.10.6
pyenv virtualenv 3.10.6 taxifare-env
pyenv global taxifare-env
```

</details>

<details>
  <summary markdown='span'><strong> ⚙️ <code>git</code> GitHub ile kimlik doğrulama (genişletmek için tıklayın)</strong></summary>

GitHub hesabınıza erişmesine izin vermek için özel anahtarınızı 🔑 _VM_'ye kopyalayın.

⚠️ Bu tek komutu VM üzerinde değil, makinenizde çalıştırın ⚠️

``` bash
INSTANCE=taxi-instance

# scp secure copy (cp) anlamına gelir
gcloud compute scp ~/.ssh/id_ed25519 $USER@$INSTANCE:~/.ssh/
```

⚠️ Ardından, VM üzerinde komut çalıştırmaya devam edin ⚠️

`ssh-agent`'i başlattıktan sonra az önce kopyaladığınız anahtarı kayıt edin:

``` bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

Sorulursa *passphrase*'inizi girin.

👉 Artık _sanal makine_'den **GitHub** hesabınızla etkileşim kurabilirsiniz
</details>

<details>
  <summary markdown='span'><strong> ⚙️ <em>Python</em> kodu GCP kimlik doğrulama (genişletmek için tıklayın)</strong></summary>

Paketinizin kodunun BigQuery veri ambarınıza erişebilmesi gerekiyor.

Bunu yapmak için, aşağıdaki komutu kullanarak hesabınıza giriş yapacağız 👇

``` bash
gcloud auth application-default login
```

❗️ Not: Tam üretim ortamında VM için en az ayrıcalık ilkesini uygulayan bir hizmet hesabı oluştururduk ancak bu geliştirme için en kolay yaklaşımdır.

Python kodunuzun artık GCP kaynaklarınıza erişebildiğini doğrulayalin. Önce, bazı paketleri yükleyin:

``` bash
pip install -U pip
pip install google-cloud-storage
```

Ardından, [_CLI_'den Python kodu çalıştırın](https://stackoverflow.com/questions/3987041/run-function-from-the-command-line). Bu, GCP kovalarınızı listelemelidir:

``` bash
python -c "from google.cloud import storage; \
    buckets = storage.Client().list_buckets(); \
    [print(b.name) for b in buckets]"
```

</details>

_VM_'niz artık şunlarla tamamen çalışır durumda:
- Kodunuzu çalıştırmak için bir python virtualenv (taxifare-env)
- _GitHub_ hesabınıza bağlanmak için kimlik bilgileri
- _GCP_ hesabınıza bağlanmak için kimlik bilgileri

Eksik olan tek şey projenizin kodu!

**🧪 Yüklemeden önce _VM Terminal_'inizde birkaç test çalıştıralım:**

- Varsayılan shell `/usr/bin/zsh`'dir
    ```bash
    echo $SHELL
    ```
- Python sürümü `3.10.6`'dır
    ```bash
    python --version
    ```
- Aktif GCP projesi `.env` dosyanızdaki `$GCP_PROJECT` ile aynıdır
    ```bash
    gcloud config list project
    ```

VM'niz artık bir veri bilimi canavarı 🔥

## Bulutta Eğitim

Buluttaki ilk eğitiminizi çalıştıralım!

**❓Projenizi sanal makinede nasıl kurarsınız ve çalıştırırsınız?**

**💻 Paketinizi klonlayın, gereksinimlerini yükleyin**

<details>
  <summary markdown='span'><strong>💡 İpucu </strong></summary>

Kodunuzu bu sözdizimi ile GitHub projenizi klonlayarak VM'ye kopyalayabilirsiniz:

```bash
git clone git@github.com:<user.github_nickname>/data-train-in-the-cloud
```

Bugünkü taxifare paketinin dizinine girin (komutu uyarlayın):

``` bash
cd <path/to/the/package/model/dir>
```

Modeli ve parametrelerini/metriklerini kaydetmek için dizinleri oluşturun:

``` bash
make reset_local_files
```

Paketinizi kullanmak için gerekli tüm parametrelerle bir `.env` dosyası oluşturun:

``` bash
cp .env.sample .env
```

`.env` dosyasının içeriğini doldurun (eksik değerleri tamamlayın, sanal makinenize özgü değerleri değiştirin):

``` bash
nano .env
```

`.env`'nizi yüklemek için `direnv`'i yükleyin:

``` bash
sudo apt update
sudo apt install -y direnv
```

ℹ️ Eğer hangi servisleri yeniden başlatacağınızı soran bir pencere çıkarsa, sadece *Enter*'a basın.

`direnv`'in çalışması için yeniden bağlanın (kullanıcı yeniden başlatmasını simüle edin):

``` bash
zsh --login
```

`.envrc`'nize izin verin:

``` bash
direnv allow .
```

taxifare paketini (ve tüm bağımlılıklarını) yükleyin!

``` bash
pip install .
```

</details>

**🔥 Önişleme ve eğitimi bulutta çalıştırın 🔥**!

``` bash
make run_all
```

<a href="/gce-train-ssh.png"><img src="/gce-train-ssh.png" height="450" alt="gce train ssh"></a>

> GCP servislerinden `Project not set` hatası? `GCP_PROJECT`'inizle aynı olması gereken bir `GCLOUD_PROJECT` ortam değişkeni ekleyebilirsiniz

🧪 Sonuca varmak için ilerlemenizi Kitt'te takip edin (VM'nizden)

```bash
make test_kitt
```

**🏋🏽‍♂️ Büyüğe Gidin: her şeyi `DATA_SIZE = 'all'` ile yeniden çalıştırın 🏋🏽‍♂️**!

**🏁 Bitirmek için VM'nizi KAPATIN 🌒**

GCP konsolundan bir VM instance'ini kolayca başlatabilir ve durdurabilirsiniz, bu hangi instance'ların çalıştığını görmenizi sağlar.

<a href="/1.png"><img src="/1.png" height="450" alt="gce vm start"></a>

<details>
  <summary markdown='span'><strong>💡 İpucu </strong></summary>

Sanal makinenizi başlatmanın ve durdurmanın daha hızlı bir yolu komut satırını kullanmaktır. Komutların tamamlanması hala biraz zaman alır, ancak GCP konsol arabiriminde gezinmeniz gerekmez.

Instance'larınızı başlatmak, durdurmak veya listelemek için `gcloud compute instances` komutuna bakın:

``` bash
INSTANCE=taxi-instance

gcloud compute instances stop $INSTANCE
gcloud compute instances list
gcloud compute instances start $INSTANCE
```
</details>

🚨 Bilgi işlem gücü ağaçlarda yetişmez 🌳, kullanmayı bıraktığınızda VM'yi **kapatmayı** unutmayın! 💸

</details>

<br>


🏁 Hatırlayın: VM'nizi `gcloud compute instances stop $INSTANCE` ile KAPATIN
