"use client";
import React from "react";
import Script from "next/script";
import Sidebar from "@/components/Sidebar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-1 w-full min-h-[100dvh] bg-gray-100 text-gray-900 font-sans selection:bg-blue-200 selection:text-blue-900">
      <Sidebar />
      <div className="flex-1 flex flex-col h-[100dvh] overflow-hidden">
        <div className="flex-1 flex flex-col overflow-hidden bg-white">
          <main className="flex-1 overflow-y-auto relative">
            {children}
          </main>
        </div>
      </div>

      {/* Google Translate — dashboard only */}
      <div id="google_translate_element" />
      <Script id="gt-init" strategy="afterInteractive">{`
        function googleTranslateElementInit(){
          new google.translate.TranslateElement({
            pageLanguage:'en',
            includedLanguages:'en,hi,ta,te,kn,bn,gu,ar,zh-CN,fr',
            autoDisplay:false
          },'google_translate_element');
        }
      `}</Script>
      <Script src="//translate.google.com/translate_a/element.js?cb=googleTranslateElementInit" strategy="afterInteractive" />
    </div>
  );
}
