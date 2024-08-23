import '../App.css'
import ChartContainer from './ChartContainer';
import Toolbar from './Toolbar';

function App() {

  return (
    <>
      <div style={{ width: '100%', margin: 'auto', paddingTop: '0px', paddingRight: '100px' }}>
        <h2>LaiskaJaakko Yöperho v0.7</h2>
        <Toolbar />
        <ChartContainer />
      </div>
    </>
  )
}

export default App
