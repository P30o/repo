#!/usr/bin/env bash

# الألوان
C_RESET='\033[0m'
C_BLUE='\033[1;34m'
C_GREEN='\033[1;32m'
C_RED='\033[1;31m'

# المسارات الأساسية
BASE_DIR="."
DEBS_DIR="$BASE_DIR/debs"
DIST_DIR="$BASE_DIR"
DEP_DIR="$DIST_DIR/depictions"

# الهوية (تؤخذ من البيئة أو قيم افتراضية)
REPO_NAME="${GHOST_REPO_NAME:-My Custom Repo}"
REPO_DESC="${GHOST_REPO_DESC:-A custom tweak repository.}"
REPO_AUTHOR="${GHOST_AUTHOR:-Developer}"
REPO_MAINTAINER="${GHOST_MAINTAINER:-Maintainer}"
BASE_URL="${GHOST_BASE_URL:-http://localhost}"

mkdir -p "$DEBS_DIR" "$DEP_DIR" "$DIST_DIR/assets"

usage() {
  echo "Usage: $0 [--rebuild-all | --update-one <deb> | --add-asset <file>]"
}

get_deb_field() {
  dpkg-deb -f "$1" "$2" 2>/dev/null | tr -d '\r'
}

# توليد صفحة HTML لكل أداة
generate_html_depiction() {
  local deb="$1"
  local pkg_id=$(get_deb_field "$deb" "Package")
  local name=$(get_deb_field "$deb" "Name")
  local version=$(get_deb_field "$deb" "Version")
  local desc=$(get_deb_field "$deb" "Description")
  local section=$(get_deb_field "$deb" "Section")
  local author=$(get_deb_field "$deb" "Author")
  
  local html_file="$DEP_DIR/${pkg_id}.html"
  
  # استخراج سجل التغييرات إذا وجد
  local changelog=$(dpkg-deb -f "$deb" "Changelog" 2>/dev/null | head -n 10)
  [ -z "$changelog" ] && changelog="• Initial release or no changelog provided."

  cat <<EOF > "$html_file"
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>$name - $REPO_NAME</title>
    <style>
        body { font-family: -apple-system, system-ui, sans-serif; background: #f0f2f5; color: #1c1e21; margin: 0; padding: 20px; line-height: 1.5; }
        .card { background: #fff; border-radius: 16px; padding: 24px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); max-width: 650px; margin: 0 auto 20px; }
        .header { display: flex; align-items: center; border-bottom: 1px solid #eee; padding-bottom: 20px; margin-bottom: 20px; }
        .icon { width: 80px; height: 80px; border-radius: 18px; margin-left: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        h1 { margin: 0; font-size: 24px; color: #007aff; }
        .meta-list { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; }
        .meta-item { background: #f8f9fa; padding: 12px; border-radius: 10px; border: 1px solid #edf0f2; }
        .label { font-size: 12px; color: #8e8e93; display: block; margin-bottom: 4px; }
        .value { font-weight: 600; font-size: 15px; }
        .desc-box { background: #fff; padding: 0; }
        .section-title { font-weight: 700; margin-bottom: 10px; color: #333; display: block; }
        .btn { display: block; background: #007aff; color: #fff; text-align: center; padding: 14px; border-radius: 12px; text-decoration: none; font-weight: 600; font-size: 16px; transition: transform 0.2s; }
        .btn:active { transform: scale(0.98); }
        .footer { text-align: center; font-size: 12px; color: #666; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <img src="../assets/icon.png" onerror="this.src='https://raw.githubusercontent.com/iosghost/iosghost.github.io/main/assets/icon.jpeg'" class="icon">
            <div>
                <h1>$name</h1>
                <span style="color:#666; font-size:14px;">$pkg_id</span>
            </div>
        </div>
        
        <div class="meta-list">
            <div class="meta-item"><span class="label">الإصدار</span><span class="value">$version</span></div>
            <div class="meta-item"><span class="label">القسم</span><span class="value">$section</span></div>
            <div class="meta-item"><span class="label">المطور</span><span class="value">${author:-$REPO_AUTHOR}</span></div>
            <div class="meta-item"><span class="label">الحجم</span><span class="value">$(du -h "$deb" | awk '{print $1}')</span></div>
        </div>

        <div class="desc-box">
            <span class="section-title">حول الأداة</span>
            <p style="margin:0; color:#444;">$desc</p>
        </div>
        
        <hr style="border:0; border-top:1px solid #eee; margin:20px 0;">
        
        <div class="desc-box">
            <span class="section-title">سجل التغييرات</span>
            <p style="margin:0; font-size:14px; color:#555; white-space: pre-wrap;">$changelog</p>
        </div>

        <a href="sileo://package/$pkg_id" class="btn">فتح في Sileo</a>
    </div>

    <div class="footer">
        $REPO_NAME - تم البناء بواسطة RepoBot ✅
    </div>
</body>
</html>
EOF
}

# بناء بيانات الملف Packages
build_packages_stanza() {
  local deb="$1"
  local pkg_id=$(get_deb_field "$deb" "Package")
  local size=$(stat -c%s "$deb")
  local md5=$(md5sum "$deb" | awk '{print $1}')
  local sha1=$(sha1sum "$deb" | awk '{print $1}')
  local sha256=$(sha256sum "$deb" | awk '{print $1}')
  
  # طباعة حقول deb الأساسية (عدا المحسوبة يدوياً)
  dpkg-deb -f "$deb" | grep -vE "^(Size|MD5Sum|SHA1|SHA256|Filename|Depiction|SileoDepiction|Description:)"
  
  # إعادة صياغة الحقول المطلوبة لـ Sileo وقواعد السورس
  echo "Description: $(get_deb_field "$deb" "Description")"
  echo "Filename: debs/$(basename "$deb")"
  echo "Size: $size"
  echo "MD5Sum: $md5"
  echo "SHA1: $sha1"
  echo "SHA256: $sha256"
  echo "Depiction: $BASE_URL/depictions/${pkg_id}.html"
  echo "SileoDepiction: $BASE_URL/depictions/${pkg_id}.html"
  echo ""
}

compress_and_release() {
  echo "📦 ضغط مستندات السورس..."
  gzip -c9 "$DIST_DIR/Packages" > "$DIST_DIR/Packages.gz"
  bzip2 -c9 "$DIST_DIR/Packages" > "$DIST_DIR/Packages.bz2"
  xz -c9 "$DIST_DIR/Packages" > "$DIST_DIR/Packages.xz"
  
  echo "📝 توليد ملف Release..."
  cat <<EOF > "$DIST_DIR/Release"
Origin: $REPO_NAME
Label: $REPO_NAME
Suite: stable
Version: 1.0
Codename: ios
Architectures: iphoneos-arm iphoneos-arm64
Components: main
Description: $REPO_DESC
EOF
}

rebuild_all() {
  echo -e "${C_BLUE}🔄 جاري إعادة البناء الشامل...${C_RESET}"
  : > "$DIST_DIR/Packages"
  for d in "$DEBS_DIR"/*.deb; do
    [ -e "$d" ] || continue
    echo "Processing: $(basename "$d")"
    generate_html_depiction "$d"
    build_packages_stanza "$d" >> "$DIST_DIR/Packages"
  done
  compress_and_release
}

update_one() {
  local deb="$1"
  [ -f "$deb" ] || { echo "File not found: $deb" >&2; exit 4; }
  
  local fname=$(basename "$deb")
  if [ "$(realpath "$deb")" != "$(realpath "$DEBS_DIR/$fname")" ]; then
    cp "$deb" "$DEBS_DIR/$fname"
  fi
  
  # تنفيذ Rebuild سريع لضمان ترتيب وصحة حقول Packages
  rebuild_all
}

add_asset() {
  local file="$1"
  [ -f "$file" ] || { echo "File not found: $file" >&2; exit 5; }
  local fname=$(basename "$file")
  local dest="$DIST_DIR/assets/$fname"
  
  if [ "$(realpath "$file")" != "$(realpath "$dest")" ]; then
    cp "$file" "$dest"
  fi
  echo "✅ Asset added: $fname"
}

main() {
  case "${1:-}" in
    --rebuild-all) rebuild_all ;;
    --update-one)  update_one "$2" ;;
    --add-asset)   add_asset "$2" ;;
    *) usage; exit 1 ;;
  esac
}

main "$@"