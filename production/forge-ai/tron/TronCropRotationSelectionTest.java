package forge.ai;

import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public final class TronCropRotationSelectionTest {
    private static Map<String,Integer> counts(Object... p){Map<String,Integer> m=new HashMap<>();for(int i=0;i<p.length;i+=2)m.put((String)p[i],(Integer)p[i+1]);return m;}
    private static Set<String> set(String... n){return new HashSet<>(Arrays.asList(n));}
    private static void req(boolean v,String m){if(!v)throw new AssertionError(m);}
    private static void reqNull(Object v,String m){req(v==null,m+" expected null, got "+v);}
    private static void reqList(List<String> a,String... e){req(a!=null,"expected list");req(a.equals(Arrays.asList(e)),"expected "+Arrays.asList(e)+" got "+a);}
    public static void main(String[] args){
        reqList(TronCropRotationSelection.allowedSacrificeNames(Arrays.asList("Urza's Mine"),counts("Urza's Mine",1),set("Urza's Mine","Urza's Power Plant","Urza's Tower")));
        reqList(TronCropRotationSelection.allowedSacrificeNames(Arrays.asList("Urza's Power Plant"),counts("Urza's Power Plant",1),set("Urza's Mine","Urza's Power Plant","Urza's Tower")));
        reqList(TronCropRotationSelection.allowedSacrificeNames(Arrays.asList("Urza's Tower"),counts("Urza's Tower",1),set("Urza's Mine","Urza's Power Plant","Urza's Tower")));
        reqList(TronCropRotationSelection.allowedSacrificeNames(Arrays.asList("Forest","Urza's Mine","Urza's Power Plant"),counts("Forest",1,"Urza's Mine",1,"Urza's Power Plant",1),set("Urza's Tower","Urza's Mine")),"Forest");
        reqList(TronCropRotationSelection.allowedSacrificeNames(Arrays.asList("Urza's Mine","Urza's Mine"),counts("Urza's Mine",2),set("Urza's Power Plant","Urza's Tower","Urza's Mine")),"Urza's Mine","Urza's Mine");
        reqNull(TronCropRotationSelection.allowedSacrificeNames(Arrays.asList("Urza's Mine"),counts("Urza's Mine",1),set("Urza's Mine")),"missing unavailable");
        reqNull(TronCropRotationSelection.allowedSacrificeNames(Arrays.asList("Forest","Urza's Mine"),counts("Urza's Mine",1,"Urza's Power Plant",1,"Urza's Tower",1),set("Urza's Mine","Urza's Power Plant","Urza's Tower")),"full Tron");
        reqNull(TronCropRotationSelection.allowedSacrificeNames(Arrays.asList("Urza's Mine"),counts("Urza's Mine",1,"Urza's Power Plant",1),set("Urza's Mine","Urza's Power Plant")),"same-piece fallback");
        System.out.println("TronCropRotationSelectionTest PASS");
    }
}
