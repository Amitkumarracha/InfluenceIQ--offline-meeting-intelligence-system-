package org.meetiq.offline;

import android.content.Context;
import android.content.SharedPreferences;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import java.security.KeyStore;
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import org.json.JSONObject;

/** Only the access token is persisted; the password is never saved. */
final class AccountSession {
    private static final String ALIAS="InfluenceIQ.account.token.v1";
    static SharedPreferences preferences(Context context) { return context.getSharedPreferences("account",Context.MODE_PRIVATE); }
    static boolean signedIn(Context context) { return preferences(context).contains("credential"); }
    static String owner(Context context) { SharedPreferences p=preferences(context); return p.getString("server","")+"/"+p.getString("user_id",""); }
    private static SecretKey key() throws Exception {
        KeyStore store=KeyStore.getInstance("AndroidKeyStore"); store.load(null);
        if(!store.containsAlias(ALIAS)) {
            KeyGenerator generator=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");
            generator.init(new KeyGenParameterSpec.Builder(ALIAS,KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build());
            return generator.generateKey();
        }
        return (SecretKey)store.getKey(ALIAS,null);
    }
    static void save(Context context,String server,JSONObject auth) throws Exception {
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding"); cipher.init(Cipher.ENCRYPT_MODE,key());
        byte[] secret=cipher.doFinal(auth.getString("token").getBytes(java.nio.charset.StandardCharsets.UTF_8));
        preferences(context).edit().putString("server",server).putString("email",auth.getString("email"))
            .putString("user_id",auth.getString("user_id")).putString("iv",Base64.encodeToString(cipher.getIV(),Base64.NO_WRAP))
            .putString("credential",Base64.encodeToString(secret,Base64.NO_WRAP)).remove("profile").commit();
    }
    static AccountClient client(Context context) throws Exception {
        SharedPreferences p=preferences(context);
        if(!signedIn(context)) throw new java.io.IOException("Sign in to your website account first");
        try {
            Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
            cipher.init(Cipher.DECRYPT_MODE,key(),new GCMParameterSpec(128,Base64.decode(p.getString("iv",""),Base64.NO_WRAP)));
            String token=new String(cipher.doFinal(Base64.decode(p.getString("credential",""),Base64.NO_WRAP)),java.nio.charset.StandardCharsets.UTF_8);
            return new AccountClient(p.getString("server",""),token);
        } catch(Exception error) { clear(context); throw new java.io.IOException("Account session unavailable. Sign in again.",error); }
    }
    static void clear(Context context) { preferences(context).edit().remove("credential").remove("iv").remove("user_id").remove("email").remove("profile").commit(); }
}
