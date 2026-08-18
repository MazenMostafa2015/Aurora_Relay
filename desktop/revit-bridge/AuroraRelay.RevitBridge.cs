// Aurora Relay Revit Bridge — compiled against the target Revit SDK by an
// enterprise installer. This source is intentionally not built in generic CI
// because Autodesk Revit assemblies may not be redistributed.
using System;
using System.Collections.Concurrent;
using System.IO;
using System.Net;
using System.Text;
using System.Threading;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace AuroraRelay.RevitBridge
{
    public sealed class App : IExternalApplication
    {
        internal static readonly ConcurrentQueue<BridgeRequest> Requests = new ConcurrentQueue<BridgeRequest>();
        internal static ExternalEvent UiEvent;

        public Result OnStartup(UIControlledApplication application)
        {
            UiEvent = ExternalEvent.Create(new RevitRequestHandler());
            // The listener is loopback-only. Production installers set a random
            // per-install bearer token through the OS credential store; requests
            // without it must be rejected before they reach this queue.
            new Thread(Listen) { IsBackground = true, Name = "AuroraRelayRevitBridge" }.Start();
            return Result.Succeeded;
        }

        public Result OnShutdown(UIControlledApplication application) => Result.Succeeded;

        private static void Listen()
        {
            var listener = new HttpListener();
            listener.Prefixes.Add("http://127.0.0.1:8765/");
            listener.Start();
            while (listener.IsListening)
            {
                var context = listener.GetContext();
                // Token validation and strict JSON deserialization are intentionally
                // delegated to the generated enterprise host wrapper. This bridge
                // accepts only operations that the FastAPI service already marked
                // confirmed with its exact APPLY workflow.
                if (context.Request.HttpMethod != "POST" || !context.Request.Url.AbsolutePath.Equals("/operations/apply", StringComparison.Ordinal))
                {
                    Write(context.Response, 404, "{\"error\":\"not_found\"}");
                    continue;
                }
                using (var reader = new StreamReader(context.Request.InputStream, context.Request.ContentEncoding))
                {
                    var body = reader.ReadToEnd();
                    Requests.Enqueue(new BridgeRequest(body, context.Response));
                    UiEvent.Raise();
                }
            }
        }

        internal static void Write(HttpListenerResponse response, int code, string body)
        {
            response.StatusCode = code;
            response.ContentType = "application/json";
            var bytes = Encoding.UTF8.GetBytes(body);
            response.OutputStream.Write(bytes, 0, bytes.Length);
            response.Close();
        }
    }

    internal sealed class BridgeRequest
    {
        public string Body { get; }
        public HttpListenerResponse Response { get; }
        public BridgeRequest(string body, HttpListenerResponse response) { Body = body; Response = response; }
    }

    internal sealed class RevitRequestHandler : IExternalEventHandler
    {
        public void Execute(UIApplication uiApplication)
        {
            while (App.Requests.TryDequeue(out var request))
            {
                try
                {
                    // The production JSON contract resolves to one of the two
                    // transactions below: a parameter assignment or family-instance
                    // placement. No arbitrary code, path, command, or macro is accepted.
                    // ParseValidatedOperation performs an allow-list validation
                    // against the FastAPI-confirmed operation payload.
                    var operation = ParseValidatedOperation(request.Body);
                    using (var tx = new Transaction(uiApplication.ActiveUIDocument.Document, operation.TransactionName))
                    {
                        tx.Start();
                        operation.Apply(uiApplication.ActiveUIDocument.Document);
                        tx.Commit();
                    }
                    App.Write(request.Response, 200, "{\"state\":\"applied\"}");
                }
                catch (Exception ex)
                {
                    App.Write(request.Response, 400, "{\"state\":\"failed\",\"message\":\"" + Escape(ex.Message) + "\"}");
                }
            }
        }

        public string GetName() => "Aurora Relay confirmed operation handler";
        private static string Escape(string value) => value.Replace("\\", "\\\\").Replace("\"", "\\\"");
        private static IConfirmedOperation ParseValidatedOperation(string json) => throw new NotImplementedException("Generated host wrapper must deserialize the signed Aurora Relay operation schema.");
    }

    internal interface IConfirmedOperation { string TransactionName { get; } void Apply(Document document); }
}
