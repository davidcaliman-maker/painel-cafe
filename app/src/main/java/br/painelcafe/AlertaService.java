package br.painelcafe;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.job.JobInfo;
import android.app.job.JobParameters;
import android.app.job.JobScheduler;
import android.app.job.JobService;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;

import org.json.JSONArray;
import org.json.JSONObject;

import java.text.NumberFormat;
import java.util.Calendar;
import java.util.Locale;
import java.util.TimeZone;

/**
 * Alerta de FORTE ALTA / FORTE BAIXA do Conilon, rodando em segundo plano (app fechado).
 *
 * A cada ~15 min (das 5h às 22h) calcula o preço do Conilon com a mesma regra do app
 * (index.html): calibração do historico.json publicado + Londres e dólar ao vivo. Compara com
 * o fechamento anterior e notifica quando a variação passa de "alertaVariacaoPct" (config.json,
 * padrão 2%). Avisa de novo a cada novo degrau (2%, 4%, 6%...) no mesmo dia.
 */
public class AlertaService extends JobService {

    private static final int JOB_ID = 1001;
    private static final String CANAL = "alertas_conilon";
    private static final String SITE = "https://davidcaliman-maker.github.io/painel-cafe/";
    private static final String SCANNER = "https://scanner.tradingview.com/";

    /** Agenda a verificação periódica (chamado ao abrir o app; sobrevive a reinicializações). */
    static void agendar(Context ctx) {
        // Criar o canal com o app aberto faz o Android 13+ pedir a permissão de notificação.
        criarCanal(ctx);
        JobScheduler js = (JobScheduler) ctx.getSystemService(Context.JOB_SCHEDULER_SERVICE);
        if (js == null) return;
        for (JobInfo j : js.getAllPendingJobs()) if (j.getId() == JOB_ID) return;
        js.schedule(new JobInfo.Builder(JOB_ID, new ComponentName(ctx, AlertaService.class))
                .setPeriodic(15 * 60 * 1000L)
                .setRequiredNetworkType(JobInfo.NETWORK_TYPE_ANY)
                .setPersisted(true)
                .build());
    }

    @Override
    public boolean onStartJob(final JobParameters params) {
        new Thread(() -> {
            try {
                verificar(getApplicationContext(), false);
            } catch (Exception ignored) {
                // Sem internet ou dados indisponíveis: tenta na próxima rodada.
            }
            jobFinished(params, false);
        }).start();
        return true;
    }

    @Override
    public boolean onStopJob(JobParameters params) {
        return false;
    }

    /** Faz uma verificação. Com "teste" = true, notifica mesmo abaixo do limite (botão de teste). */
    static void verificar(Context ctx, boolean teste) throws Exception {
        Calendar agora = Calendar.getInstance(TimeZone.getTimeZone("America/Sao_Paulo"));
        int hora = agora.get(Calendar.HOUR_OF_DAY);
        if (!teste && (hora < 5 || hora >= 22)) return;

        long t = System.currentTimeMillis();
        JSONObject cfg = new JSONObject(MainActivity.http(SITE + "config.json?t=" + t, null));
        JSONObject hist = new JSONObject(MainActivity.http(SITE + "historico.json?t=" + t, null));
        JSONObject cal = hist.getJSONObject("calibracao");
        String ctr = hist.getJSONObject("contratos").getString("londres");
        String ctrCal = cal.getString("contrato");
        double ajuste = cal.optDouble("ajusteConilonCepea", 0);

        JSONObject fut = scan("futures", "[\"ICEEUR:" + ctr + "\",\"ICEEUR:" + ctrCal + "\"]");
        JSONObject fx = scan("forex", "[\"FX_IDC:USDBRL\"]");
        JSONArray q = fut.getJSONArray("ICEEUR:" + ctr);
        double usd = Math.round(fx.getJSONArray("FX_IDC:USDBRL").getDouble(0) * 100) / 100.0;
        double londres = q.getDouble(0);

        // Mesma regra do app: estimativa pela bolsa se Londres já negociou depois do último Cepea.
        String sessao = isoUTC(q.getLong(1));
        double ajTroca = 0;
        if (!ctrCal.equals(ctr) && fut.has("ICEEUR:" + ctrCal)) {
            ajTroca = anterior(fut.getJSONArray("ICEEUR:" + ctrCal)) - anterior(q);
        }
        String dataCal = cal.getString("data");
        boolean estimativa = sessao.compareTo(dataCal) > 0 || ajTroca != 0;

        double preco, refPreco;
        String refData;
        if (estimativa) {
            preco = (londres + cal.getDouble("diferencialConilon") + ajTroca) * 0.06 * usd;
            refPreco = cal.getDouble("cepeaConilon") + ajuste;
            refData = dataCal;
        } else {
            preco = cal.getDouble("precoConilon");
            JSONArray dias = hist.getJSONArray("dias");
            JSONObject ant = null;
            for (int i = 0; i < dias.length(); i++) {
                JSONObject d = dias.getJSONObject(i);
                if (d.has("cepeaConilon") && d.getString("data").compareTo(dataCal) < 0) ant = d;
            }
            if (ant == null) return;
            refPreco = ant.getDouble("cepeaConilon") + ajuste;
            refData = ant.getString("data");
        }

        double varPct = (preco / refPreco - 1) * 100;
        double limite = cfg.optDouble("alertaVariacaoPct", 2.0);
        if (limite <= 0) return;  // alertas desligados no config.json

        // Degrau atingido (2% → 1, 4% → 2...). Só notifica quando sobe de degrau no mesmo dia.
        int degrau = (int) Math.floor(Math.abs(varPct) / limite);
        String chave = "nivel_" + refData + "_" + (varPct >= 0 ? "alta" : "baixa");
        SharedPreferences sp = ctx.getSharedPreferences("alertas", MODE_PRIVATE);
        if (!teste) {
            if (degrau < 1 || degrau <= sp.getInt(chave, 0)) return;
            sp.edit().putInt(chave, degrau).apply();
        }
        notificar(ctx, varPct, preco, preco - refPreco, refData, estimativa, teste);
    }

    private static void notificar(Context ctx, double varPct, double preco, double difReais,
                                  String refData, boolean estimativa, boolean teste) {
        NotificationManager nm = (NotificationManager) ctx.getSystemService(NOTIFICATION_SERVICE);
        if (nm == null) return;
        criarCanal(ctx);
        NumberFormat nf = NumberFormat.getNumberInstance(new Locale("pt", "BR"));
        nf.setMinimumFractionDigits(2);
        nf.setMaximumFractionDigits(2);
        boolean alta = varPct >= 0;
        String titulo = (teste ? "TESTE · " : "") + (alta ? "▲ FORTE ALTA" : "▼ FORTE BAIXA") + " do Conilon";
        String dia = refData.substring(8, 10) + "/" + refData.substring(5, 7);
        String texto = "R$ " + nf.format(preco) + "  (" + (alta ? "+" : "−") + nf.format(Math.abs(varPct)) + "% · "
                + (alta ? "+" : "−") + "R$ " + nf.format(Math.abs(difReais)) + ")\n"
                + "Em relação ao fechamento de " + dia + (estimativa ? " · estimativa pela bolsa" : " · fechamento Cepea");

        PendingIntent abrir = PendingIntent.getActivity(ctx, 0, new Intent(ctx, MainActivity.class),
                PendingIntent.FLAG_UPDATE_CURRENT | (Build.VERSION.SDK_INT >= 23 ? PendingIntent.FLAG_IMMUTABLE : 0));
        Notification.Builder b = Build.VERSION.SDK_INT >= 26
                ? new Notification.Builder(ctx, CANAL) : new Notification.Builder(ctx);
        b.setSmallIcon(R.drawable.ic_notificacao)
                .setContentTitle(titulo)
                .setContentText(texto.split("\n")[0])
                .setStyle(new Notification.BigTextStyle().bigText(texto))
                .setColor(alta ? 0xFF1F8F3A : 0xFFC4161C)
                .setContentIntent(abrir)
                .setAutoCancel(true);
        if (Build.VERSION.SDK_INT < 26) {
            b.setPriority(Notification.PRIORITY_HIGH).setDefaults(Notification.DEFAULT_ALL);
        }
        nm.notify(alta ? 1 : 2, b.build());
    }

    private static void criarCanal(Context ctx) {
        if (Build.VERSION.SDK_INT < 26) return;
        NotificationManager nm = (NotificationManager) ctx.getSystemService(NOTIFICATION_SERVICE);
        if (nm == null) return;
        NotificationChannel canal = new NotificationChannel(CANAL, "Alertas do Conilon",
                NotificationManager.IMPORTANCE_HIGH);
        canal.setDescription("Forte alta ou forte baixa no preço do Conilon");
        nm.createNotificationChannel(canal);
    }

    private static JSONObject scan(String mercado, String tickers) throws Exception {
        String corpo = "{\"symbols\":{\"tickers\":" + tickers + "},\"columns\":[\"close\",\"time\",\"close[1]\"]}";
        JSONArray data = new JSONObject(MainActivity.http(SCANNER + mercado + "/scan", corpo)).getJSONArray("data");
        JSONObject out = new JSONObject();
        for (int i = 0; i < data.length(); i++) {
            JSONObject r = data.getJSONObject(i);
            out.put(r.getString("s"), r.getJSONArray("d"));
        }
        return out;
    }

    /** Fechamento anterior (close[1]); se faltar, o último preço. */
    private static double anterior(JSONArray q) throws Exception {
        return q.isNull(2) ? q.getDouble(0) : q.getDouble(2);
    }

    private static String isoUTC(long segundos) {
        Calendar c = Calendar.getInstance(TimeZone.getTimeZone("UTC"));
        c.setTimeInMillis(segundos * 1000);
        return String.format(Locale.US, "%04d-%02d-%02d",
                c.get(Calendar.YEAR), c.get(Calendar.MONTH) + 1, c.get(Calendar.DAY_OF_MONTH));
    }
}
