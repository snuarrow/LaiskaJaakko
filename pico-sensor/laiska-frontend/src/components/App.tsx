import "../App.css";
import ChartContainer from "./ChartContainer";
import Toolbar from "./Toolbar";

function App() {
  return (
    <>
      <div
        className="appcontainer"
      >
        <h2 className="appheader">LaiskaJaakko Yöperho v0.7</h2>
        <Toolbar />
        <ChartContainer />
      </div>
    </>
  );
}

export default App;
