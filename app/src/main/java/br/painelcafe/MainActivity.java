package br.painelcafe;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/**
 * Tela única: um WebView que carrega a interface publicada no GitHub Pages,
 * assim qualquer mudança no index.html chega ao app sem reinstalar o APK.
 * Sem internet, usa o cache do WebView/service worker e, por último, a cópia
 * embutida em assets/index.html.
 * As requisições HTTP são feitas aqui no Java (sem restrição de CORS) e
 * devolvidas ao JavaScript via callback.
 */
public class MainActivity extends Activity {

    private static final String SITE = "https://davidcaliman-maker.github.io/painel-cafe/";
    private static final String OFFLINE = "file:///android_asset/index.html";

    private WebView web;
    private SharedPreferences prefs;

    @SuppressLint({"SetJavaScriptEnabled", "AddJavascriptInterface"})
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        prefs = getSharedPreferences("painel", MODE_PRIVATE);

        web = new WebView(this);
        web.setBackgroundColor(0xFF000000);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        web.addJavascriptInterface(new Bridge(), "Native");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                String url = req.getUrl().toString();
                if (url.startsWith(SITE) || url.startsWith("file:///android_asset/")) return false;
                openExternal(url);  // links de fora (ex.: WhatsApp) abrem no app correspondente
                return true;
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest req, WebResourceError err) {
                // Sem internet e sem cache: cai para a cópia embutida no APK.
                if (req.isForMainFrame() && req.getUrl().toString().startsWith(SITE)) {
                    view.loadUrl(OFFLINE);
                }
            }
        });
        setContentView(web);
        web.loadUrl(SITE);
        AlertaService.agendar(this);  // alertas de forte alta/baixa em segundo plano
    }

    private void openExternal(String url) {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
        } catch (Exception ignored) {
        }
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) web.goBack();
        else super.onBackPressed();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (web != null) web.evaluateJavascript("window.onAppResume && onAppResume()", null);
    }

    private class Bridge {

        /** POST JSON assíncrono; o resultado chega em window.__nativeCb(id, ok, texto). */
        @JavascriptInterface
        public void post(final String url, final String body, final String cbId) {
            request(url, body, cbId);
        }

        /** GET assíncrono; mesmo callback do post. */
        @JavascriptInterface
        public void get(final String url, final String cbId) {
            request(url, null, cbId);
        }

        private void request(final String url, final String body, final String cbId) {
            new Thread(() -> {
                boolean ok;
                String result;
                try {
                    result = http(url, body);
                    ok = true;
                } catch (Exception e) {
                    result = String.valueOf(e.getMessage());
                    ok = false;
                }
                final String js = "window.__nativeCb(" + quote(cbId) + "," + ok + "," + quote(result) + ")";
                runOnUiThread(() -> web.evaluateJavascript(js, null));
            }).start();
        }

        /** Abre um link externo (ex.: WhatsApp) no app correspondente. */
        @JavascriptInterface
        public void openUrl(final String url) {
            runOnUiThread(() -> openExternal(url));
        }

        /** Botão "Testar alerta" (tela de ajuda): mostra uma notificação com o preço de agora. */
        @JavascriptInterface
        public void testarAlerta() {
            new Thread(() -> {
                try {
                    AlertaService.verificar(getApplicationContext(), true);
                } catch (Exception ignored) {
                }
            }).start();
        }

        @JavascriptInterface
        public String load(String key) {
            return prefs.getString(key, null);
        }

        @JavascriptInterface
        public void save(String key, String value) {
            prefs.edit().putString(key, value).apply();
        }
    }

    /** GET quando body é null; senão POST com JSON. */
    static String http(String url, String body) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setConnectTimeout(30000);
        c.setReadTimeout(30000);
        c.setRequestProperty("User-Agent", "Mozilla/5.0 (Android) PainelCafe/1.0");
        if (body != null) {
            c.setRequestMethod("POST");
            c.setDoOutput(true);
            c.setRequestProperty("Content-Type", "application/json");
            try (OutputStream os = c.getOutputStream()) {
                os.write(body.getBytes(StandardCharsets.UTF_8));
            }
        }
        int code = c.getResponseCode();
        InputStream in = code >= 400 ? c.getErrorStream() : c.getInputStream();
        ByteArrayOutputStream buf = new ByteArrayOutputStream();
        byte[] b = new byte[8192];
        int n;
        while (in != null && (n = in.read(b)) > 0) buf.write(b, 0, n);
        c.disconnect();
        if (code >= 400) throw new Exception("HTTP " + code);
        return buf.toString("UTF-8");
    }

    /** Converte uma string Java em literal JavaScript seguro. */
    private static String quote(String s) {
        StringBuilder sb = new StringBuilder("\"");
        for (char ch : s.toCharArray()) {
            switch (ch) {
                case '"': sb.append("\\\""); break;
                case '\\': sb.append("\\\\"); break;
                case '\n': sb.append("\\n"); break;
                case '\r': sb.append("\\r"); break;
                case ' ': sb.append("\\u2028"); break;
                case ' ': sb.append("\\u2029"); break;
                default:
                    if (ch < 0x20) sb.append(String.format("\\u%04x", (int) ch));
                    else sb.append(ch);
            }
        }
        return sb.append('"').toString();
    }
}
