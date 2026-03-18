import os
import tarfile
import string

TYPE_SIG_FILE = "ujrnl_type.sig"
LOG_FILE = "ujrnl_log.txt"

def to_printable(data: bytes) -> str:
    result = ""
    for b in data:
        ch = chr(b)
        if ch in string.printable and ch not in "\r\n\t":
            result += ch
        else:
            result += "."
    return result

def load_type_signature(base_dir: str):
    path = os.path.join(base_dir, TYPE_SIG_FILE)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        sig = f.read(4)
    return sig if len(sig) == 4 else None

def save_type_signature(base_dir: str, sig: bytes):
    path = os.path.join(base_dir, TYPE_SIG_FILE)
    with open(path, "wb") as f:
        f.write(sig)

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")

    logfile = open(LOG_FILE, "w", encoding="utf-8")

    type_sig = load_type_signature(base_dir)

    stats = {
        "total_archives": 0,
        "opened_archives": 0,
        "ujrnl_found": 0,
        "ujrnl_read": 0,
        "ujrnl_missing": 0,
        "errors": 0,
        "type_match": 0,
        "type_mismatch": 0,
        "type_unknown": 0,
    }

    per_file_report = {}

    for filename in os.listdir(data_dir):
        if not filename.endswith(".tar.gz"):
            continue

        stats["total_archives"] += 1
        tar_path = os.path.join(data_dir, filename)
        per_file_report[filename] = {"status": "OK", "details": ""}

        print(f"\n=== {filename} ===")

        try:
            try:
                tar = tarfile.open(tar_path, "r:gz")
            except Exception as e:
                per_file_report[filename]["status"] = "Ошибка открытия архива"
                per_file_report[filename]["details"] = str(e)
                stats["errors"] += 1
                print("Ошибка открытия архива:", e)
                continue

            stats["opened_archives"] += 1

            ujrnl_member = None
            for m in tar.getmembers():
                if m.isfile() and m.name.lower().endswith(".ujrnl"):
                    ujrnl_member = m
                    break

            if ujrnl_member is None:
                stats["ujrnl_missing"] += 1
                per_file_report[filename]["status"] = "Нет файла .UJRNL"
                print("Файл .UJRNL не найден")
                tar.close()
                continue

            stats["ujrnl_found"] += 1

            try:
                f = tar.extractfile(ujrnl_member)
                if f is None:
                    raise ValueError("extractfile() вернул None")
            except Exception as e:
                stats["errors"] += 1
                per_file_report[filename]["status"] = "Ошибка извлечения .UJRNL"
                per_file_report[filename]["details"] = str(e)
                print("Ошибка извлечения файла:", e)
                tar.close()
                continue

            raw = f.read(60)

            if len(raw) < 4:
                stats["type_unknown"] += 1
                per_file_report[filename]["status"] = "Слишком короткий .UJRNL (<4 байт)"
                print("Файл .UJRNL короче 4 байт")
            else:
                file_sig = raw[:4]

                if type_sig is None:
                    type_sig = file_sig
                    save_type_signature(base_dir, type_sig)
                    print(f"Эталонный тип сохранён в {TYPE_SIG_FILE}")

                if file_sig == type_sig:
                    stats["type_match"] += 1
                    print("Тип совпал")
                else:
                    stats["type_mismatch"] += 1
                    per_file_report[filename]["status"] = "Несовпадение типа (первые 4 байта)"
                    print("Тип НЕ совпал")

            printable = to_printable(raw)
            print("PRINTABLE:", printable)

            stats["ujrnl_read"] += 1
            tar.close()

        except Exception as e:
            stats["errors"] += 1
            per_file_report[filename]["status"] = "Неизвестная ошибка"
            per_file_report[filename]["details"] = str(e)
            print("Неизвестная ошибка:", e)

    # --- ЛОГ-ФАЙЛ (только итог и отчёт) ---
    logfile.write("==================== ИТОГ ====================\n")
    logfile.write(f"Архивов найдено:            {stats['total_archives']}\n")
    logfile.write(f"Архивов успешно открыто:    {stats['opened_archives']}\n")
    logfile.write(f"Файлов .UJRNL найдено:      {stats['ujrnl_found']}\n")
    logfile.write(f"Файлов .UJRNL прочитано:    {stats['ujrnl_read']}\n")
    logfile.write(f".UJRNL отсутствует:         {stats['ujrnl_missing']}\n")
    logfile.write(f"Ошибок при обработке:       {stats['errors']}\n")
    logfile.write(f"Тип совпал:                 {stats['type_match']}\n")
    logfile.write(f"Тип НЕ совпал:              {stats['type_mismatch']}\n")
    logfile.write(f"Тип не удалось определить:  {stats['type_unknown']}\n")
    logfile.write("==============================================\n\n")

    logfile.write("Детальный отчёт по каждому архиву:\n")
    for fname, info in per_file_report.items():
        logfile.write(f"- {fname}: {info['status']}\n")
        if info["details"]:
            logfile.write(f"    Причина: {info['details']}\n")

    logfile.close()

    # --- ИТОГ В КОНСОЛЬ ---
    print("\n==================== ИТОГ ====================")
    print(f"Архивов найдено:            {stats['total_archives']}")
    print(f"Архивов успешно открыто:    {stats['opened_archives']}")
    print(f"Файлов .UJRNL найдено:      {stats['ujrnl_found']}")
    print(f"Файлов .UJRNL прочитано:    {stats['ujrnl_read']}")
    print(f".UJRNL отсутствует:         {stats['ujrnl_missing']}")
    print(f"Ошибок при обработке:       {stats['errors']}")
    print(f"Тип совпал:                 {stats['type_match']}")
    print(f"Тип НЕ совпал:              {stats['type_mismatch']}")
    print(f"Тип не удалось определить:  {stats['type_unknown']}")
    print("==============================================")

    print("\nДетальный отчёт по каждому архиву:")
    for fname, info in per_file_report.items():
        print(f"- {fname}: {info['status']}")
        if info["details"]:
            print(f"    Причина: {info['details']}")

if __name__ == "__main__":
    main()
