import numpy as np
import pandas as pd

from pathlib import Path
from colorama import Fore, Style
from dateutil.parser import parse

from taxifare.params import *
from taxifare.ml_logic.data import get_data_with_cache, clean_data, load_data_to_bq
from taxifare.ml_logic.model import initialize_model, compile_model, train_model, evaluate_model
from taxifare.ml_logic.preprocessor import preprocess_features
from taxifare.ml_logic.registry import load_model, save_model, save_results

def preprocess(min_date:str = '2009-01-01', max_date:str = '2015-01-01') -> None:
    """
    - Query the raw dataset from WorkinTech's BigQuery dataset
    - Cache query result as a local CSV if it doesn't exist locally
    - Process query data
    - Store processed data on your personal BQ (truncate existing table if it exists)
    - No need to cache processed data as CSV (it will be cached when queried back from BQ during training)
    """

    print(Fore.MAGENTA + "\n ⭐️ Use case: preprocess" + Style.RESET_ALL)

    # Query raw data from BigQuery using `get_data_with_cache`
    min_date = parse(min_date).strftime('%Y-%m-%d') # e.g '2009-01-01'
    max_date = parse(max_date).strftime('%Y-%m-%d') # e.g '2009-01-01'

    # Önceki projeden referansla query değişkeni:
    # GCP_PROJECT_WAGON yerine params.py'da tanımlı GCP_PROJECT_WORKINTECH kullanıyoruz.
    query = f"""
        SELECT {",".join(COLUMN_NAMES_RAW)}
        FROM `{GCP_PROJECT_WORKINTECH}`.{BQ_DATASET}.{BQ_DATASET}_{DATA_SIZE}
        WHERE pickup_datetime BETWEEN '{min_date}' AND '{max_date}'
        ORDER BY pickup_datetime
    """

    # 1. Veriyi Çek (Get Data)
    # Ham veriyi yerel diske cache'ler, varsa oradan okur.
    data_query_cache_path = Path(LOCAL_DATA_PATH).joinpath("raw", f"query_{min_date}_{max_date}_{DATA_SIZE}.csv")
    data_query = get_data_with_cache(
        gcp_project=GCP_PROJECT, # Sorgu maliyetini kendi projemiz üstlenir
        query=query,
        cache_path=data_query_cache_path,
        data_has_header=True
    )

    # 2. Veriyi İşle (Process Data)
    # Temizleme ve Ön İşleme adımları
    data_clean = clean_data(data_query)
    
    # X ve y ayrımı
    X = data_clean.drop("fare_amount", axis=1)
    y = data_clean[["fare_amount"]]
    
    # Özellikleri işle (numpy array döner)
    X_processed = preprocess_features(X)

    # 3. BigQuery'e Yükle (Load to BQ)
    # İşlenmiş veriyi (X_processed + y) tek bir DataFrame olarak birleştir
    # BQ'ya yüklemek için DataFrame formatında olmalı.
    data_processed_df = pd.DataFrame(
        np.concatenate((X_processed, y), axis=1)
    )
    
    # Sütun isimleri BQ'da çok önemli değil ama tutarlılık için eklenebilir, 
    # şimdilik otomatik isimlendirme ile yüklüyoruz.
    load_data_to_bq(
        data_processed_df,
        gcp_project=GCP_PROJECT,
        bq_dataset=BQ_DATASET,
        table=f"processed_{DATA_SIZE}",
        truncate=True # Her seferinde tabloyu sıfırdan oluştur
    )

    print("✅ preprocess() done \n")

def train(
        min_date:str = '2009-01-01',
        max_date:str = '2015-01-01',
        split_ratio: float = 0.02, # 0.02 represents ~ 1 month of validation data on a 2009-2015 train set
        learning_rate=0.0005,
        batch_size = 256,
        patience = 2
    ) -> float:

    """
    - Download processed data from your BQ table (or from cache if it exists)
    - Train on the preprocessed dataset (which should be ordered by date)
    - Store training results and model weights

    Return val_mae as a float
    """

    print(Fore.MAGENTA + "\n⭐️ Use case: train" + Style.RESET_ALL)
    print(Fore.BLUE + "\nLoading preprocessed validation data..." + Style.RESET_ALL)

    min_date = parse(min_date).strftime('%Y-%m-%d') # e.g '2009-01-01'
    max_date = parse(max_date).strftime('%Y-%m-%d') # e.g '2009-01-01'

    # Load processed data using `get_data_with_cache` in chronological order
    
    # 1. İşlenmiş veriyi kendi BQ tablomuzdan çekmek için sorgu
    # NOT: Preprocess aşamasında veriyi zaten işleyip yüklediğimiz için 
    # burada sadece "SELECT *" yapıyoruz.
    query = f"""
        SELECT *
        FROM `{GCP_PROJECT}`.{BQ_DATASET}.processed_{DATA_SIZE}
    """
    
    data_processed_cache_path = Path(LOCAL_DATA_PATH).joinpath("processed", f"processed_{min_date}_{max_date}_{DATA_SIZE}.csv")
    
    data_processed = get_data_with_cache(
        gcp_project=GCP_PROJECT,
        query=query,
        cache_path=data_processed_cache_path,
        data_has_header=False # Preprocess çıktısında header yoktu
    )
    
    # Veri gelmezse işlemi durdur
    if data_processed.shape[0] < 10:
        print("❌ Not enough data, probably empty...")
        return None

    # 2. Train/Val Ayrımı (Split)
    # Veri zaten tarih sırasına göre geldiği için (BQ'ya öyle yüklemiştik veya yüklerken sıralıydı)
    # sondan ayırabiliriz.
    train_length = int(len(data_processed) * (1 - split_ratio))
    
    # Numpy array'e çevir
    data_processed_np = data_processed.to_numpy()
    
    df_train = data_processed_np[:train_length, :]
    df_val = data_processed_np[train_length:, :]
    
    # X ve y ayrımı (son sütun y, öncekiler X)
    X_train_processed = df_train[:, :-1]
    y_train = df_train[:, -1]
    
    X_val_processed = df_val[:, :-1]
    y_val = df_val[:, -1]

    # 3. Model Eğitimi (Train)
    model = initialize_model(input_shape=X_train_processed.shape[1:])
    model = compile_model(model, learning_rate=learning_rate)
    
    model, history = train_model(
        model, 
        X_train_processed, 
        y_train,
        batch_size=batch_size,
        patience=patience,
        validation_data=(X_val_processed, y_val)
    )

    val_mae = np.min(history.history['val_mae'])

    params = dict(
        context="train",
        training_set_size=DATA_SIZE,
        row_count=len(X_train_processed),
    )

    # Save results on the hard drive using taxifare.ml_logic.registry
    save_results(params=params, metrics=dict(mae=val_mae))

    # Save model weight on the hard drive (and optionally on GCS too!)
    save_model(model=model)

    print("✅ train() done \n")

    return val_mae

def evaluate(
        min_date:str = '2014-01-01',
        max_date:str = '2015-01-01',
        stage: str = "Production"
    ) -> float:
    """
    Evaluate the performance of the latest production model on processed data
    Return MAE as a float
    """
    print(Fore.MAGENTA + "\n⭐️ Use case: evaluate" + Style.RESET_ALL)

    model = load_model(stage=stage)
    assert model is not None

    min_date = parse(min_date).strftime('%Y-%m-%d') # e.g '2009-01-01'
    max_date = parse(max_date).strftime('%Y-%m-%d') # e.g '2009-01-01'

    # Query your BigQuery processed table and get data_processed using `get_data_with_cache`
    
    # 1. Değerlendirme verisini çek
    query = f"""
        SELECT *
        FROM `{GCP_PROJECT}`.{BQ_DATASET}.processed_{DATA_SIZE}
        WHERE CAST(int64_field_4 AS FLOAT64) >= 0 
    """
    # NOT: Processed tabloda tarih sütunu kaybolduğu için (işlenmiş float'a döndü)
    # normalde tarih filtresi yapamayız. 
    # Ancak basitlik adına tüm tabloyu çekip test edebiliriz veya
    # preprocess aşamasında tarihi de saklamamız gerekirdi.
    # Şimdilik yukarıdaki train mantığıyla tüm veriyi çekelim:
    
    query = f"""
        SELECT *
        FROM `{GCP_PROJECT}`.{BQ_DATASET}.processed_{DATA_SIZE}
    """
    
    data_processed_cache_path = Path(LOCAL_DATA_PATH).joinpath("processed", f"processed_{min_date}_{max_date}_{DATA_SIZE}.csv")
    
    data_processed = get_data_with_cache(
        gcp_project=GCP_PROJECT,
        query=query,
        cache_path=data_processed_cache_path,
        data_has_header=False
    )

    if data_processed.shape[0] == 0:
        print("❌ No data to evaluate on")
        return None

    data_processed = data_processed.to_numpy()

    # X ve y ayrımı
    X_new = data_processed[:, :-1]
    y_new = data_processed[:, -1]

    metrics_dict = evaluate_model(model=model, X=X_new, y=y_new)
    mae = metrics_dict["mae"]

    params = dict(
        context="evaluate", # Package behavior
        training_set_size=DATA_SIZE,
        row_count=len(X_new)
    )

    save_results(params=params, metrics=metrics_dict)

    print("✅ evaluate() done \n")

    return mae


def pred(X_pred: pd.DataFrame = None) -> np.ndarray:
    """
    Make a prediction using the latest trained model
    """

    print("\n⭐️ Use case: predict")

    if X_pred is None:
        X_pred = pd.DataFrame(dict(
        pickup_datetime=[pd.Timestamp("2013-07-06 17:18:00", tz='UTC')],
        pickup_longitude=[-73.950655],
        pickup_latitude=[40.783282],
        dropoff_longitude=[-73.984365],
        dropoff_latitude=[40.769802],
        passenger_count=[1],
    ))

    model = load_model()
    assert model is not None

    X_processed = preprocess_features(X_pred)
    y_pred = model.predict(X_processed)

    print("\n✅ prediction done: ", y_pred, y_pred.shape, "\n")
    return y_pred


if __name__ == '__main__':
    preprocess(min_date='2009-01-01', max_date='2015-01-01')
    train(min_date='2009-01-01', max_date='2015-01-01')
    evaluate(min_date='2009-01-01', max_date='2015-01-01')
    pred()